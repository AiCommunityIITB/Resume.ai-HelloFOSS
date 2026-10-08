import sys
sys.path.append('/workspace/Resume.ai/backend')
import os
import json
import pandas as pd
import numpy as np
from cerebras.cloud.sdk import Cerebras
from tabulate import tabulate
from sqlalchemy import create_engine, MetaData, Column, Integer, String, Float, Text, Boolean, LargeBinary, NVARCHAR, text
from sqlalchemy.types import TypeDecorator, SMALLINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
import re
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Dict, List, Tuple, Any
import concurrent.futures
from threading import Lock
import threading
from dotenv import load_dotenv
import sqlite3
from database_models.resume_models import Project, WorkExperience
from utils.database import projects_engine, workex_engine, ProjectsBase, WorkexBase

# Optional imports for embedding functionality
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import pickle
    EMBEDDING_SUPPORT = True
except ImportError as e:
    print(f"Warning: Embedding functionality not available - {e}")
    print("Install with: pip install sentence-transformers scikit-learn")
    EMBEDDING_SUPPORT = False
    SentenceTransformer = None
    cosine_similarity = None
    pickle = None

load_dotenv()

_model_cache = {}
_model_lock = Lock()

# Custom Boolean type that maps to SQL Server BIT (same as migration script)
class SQLServerBoolean(TypeDecorator):
    """Custom boolean type that maps to SQL Server BIT"""
    impl = SMALLINT
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'mssql':
            return dialect.type_descriptor(SMALLINT())
        else:
            return dialect.type_descriptor(Boolean())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return 1 if value else 0
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return bool(value)

class ProjectAnalyzer:
    
    def __init__(self, engine, base, db_type, max_workers=16, max_concurrent_per_key=5):
        # Load multiple API keys
        self.api_keys = [
            os.getenv('CEREBRAS_API_KEY_1'),
            os.getenv('CEREBRAS_API_KEY_2'),
            os.getenv('CEREBRAS_API_KEY_3'),
            os.getenv('CEREBRAS_API_KEY_4'),
            os.getenv('CEREBRAS_API_KEY_5'),
            os.getenv('CEREBRAS_API_KEY_6'),
            os.getenv('CEREBRAS_API_KEY_7'),
            os.getenv('CEREBRAS_API_KEY_8')
        ]
        
        self.api_keys = [key for key in self.api_keys if key is not None]
        
        if not self.api_keys:
            single_key = os.getenv('CEREBRAS_API_KEY')
            if single_key:
                self.api_keys = [single_key]
            else:
                raise ValueError("No valid API keys found. Please set CEREBRAS_API_KEY or CEREBRAS_API_KEY_1, CEREBRAS_API_KEY_2, etc.")
        
        self.clients = [Cerebras(api_key=key) for key in self.api_keys]
        
        self.client = self.clients[0]
        
        self.max_workers = max_workers
        self.max_concurrent_per_key = max_concurrent_per_key
        
        self.key_semaphores = [threading.Semaphore(max_concurrent_per_key) for _ in self.api_keys]
        self.request_count = 0
        self.requests_per_key = {i: 0 for i in range(len(self.api_keys))}
        self.stats_lock = Lock()
        
        self.is_workex_db = (db_type == "workex")
        
        self.engine = engine
        
        # Check if we're using SQL Server
        self.is_sql_server = 'mssql' in str(engine.url).lower() or 'sql server' in str(engine.url).lower()
        
        Session = sessionmaker(bind=self.engine)
        self.session_factory = Session
        
        self.category_models: Dict[str, Any] = {}

        self.Base = base
        
        # Get script directory for loading prompts
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.scoring_prompts = {
            'design': self._load_prompt(os.path.join(script_dir, 'prompts/promptDesign.md')),
            'non_tech': self._load_prompt(os.path.join(script_dir, 'prompts/promptNonTech.md')),
            'default': self._load_prompt(os.path.join(script_dir, 'prompts/promptV2.md'))
        }
        self.tagging_prompt = self._load_prompt(os.path.join(script_dir, 'prompts/reclassificationPromptV2.md'))
        
        self._load_all_category_models()
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-pro')
        else:
            self.gemini_model = None
            print("Warning: GEMINI_API_KEY not found. Project suggestions will be disabled.")
        
        # Initialize sentence transformer for embeddings
        if EMBEDDING_SUPPORT:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.sentence_model = None
        
        # Load embeddings cache
        self.embeddings_cache: Dict[str, Dict] = {}
        self._load_embeddings_cache_sql_server()

    def _load_all_category_models(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tech_stack_dir = os.path.join(script_dir, 'TechStack')
        
        if not os.path.isdir(tech_stack_dir):
            return
            
        for filename in os.listdir(tech_stack_dir):
            if filename.endswith('_technologies.txt'):
                category = filename.replace('_technologies.txt', '')
                try:
                    with open(os.path.join(tech_stack_dir, filename), 'r', encoding='utf-8') as file:
                        technologies = file.read().strip()
                    tech_list = technologies.split('\n')
                    if tech_list == ['']:
                        tech_list = []
                    self._create_category_model(category, tech_list)
                except Exception as e:
                    pass

    def _load_embeddings_cache_sql_server(self):
        """Load all embeddings from database into memory for fast similarity search."""
        if not EMBEDDING_SUPPORT:
            print("Embedding functionality not available - skipping cache loading")
            return
            
        print("Loading embeddings cache from database...")
        
        try:
            session = self.session_factory()
            
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            print(f"Found {len(all_tables)} tables in database")
            
            db_prefix = 'workex' if self.is_workex_db else 'projects'
            
            engine_url = str(self.engine.url).lower()
            is_sqlite = 'sqlite' in engine_url
            is_mssql = 'mssql' in engine_url or 'sql server' in engine_url
            
            if is_sqlite:
                length_function = "LENGTH"
            elif is_mssql:
                length_function = "LEN"
            else:
                length_function = "LENGTH"
            
            for table_name in all_tables:
                try:
                    columns_info = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns_info]
                    
                    if 'embedding' not in column_names:
                        continue
                    
                    if is_mssql:
                        quoted_table = f"[{table_name}]"
                    else:
                        quoted_table = table_name
                    
                    count_query = f"""
                        SELECT COUNT(*) FROM {quoted_table} 
                        WHERE embedding IS NOT NULL AND {length_function}(embedding) > 0
                    """
                    
                    result = session.execute(text(count_query))
                    embedding_count = result.scalar()
                    
                    if embedding_count == 0:
                        print(f"Table '{table_name}' has no embeddings, skipping...")
                        continue
                    
                    load_query = f"""
                        SELECT embedding FROM {quoted_table} 
                        WHERE embedding IS NOT NULL AND {length_function}(embedding) > 0
                    """
                    
                    result = session.execute(text(load_query))
                    rows = result.fetchall()
                    
                    if not rows:
                        continue
                    
                    cache_key = f"{db_prefix}_{table_name}"
                    embeddings = []
                    
                    print(f"Processing {len(rows)} embeddings for table '{table_name}'...")
                    
                    for row in rows:
                        try:
                            embedding_bytes = row[0]
                            if embedding_bytes:
                                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                                embeddings.append(embedding)
                        except Exception as e:
                            print(f"Error processing embedding: {e}")
                            continue
                    
                    if embeddings:
                        self.embeddings_cache[cache_key] = np.array(embeddings)
                        print(f"Loaded {len(embeddings)} embeddings for {cache_key}")
                    else:
                        print(f"No valid embeddings found for table '{table_name}'")
                
                except Exception as e:
                    print(f"Error processing table {table_name}: {e}")
                    continue
            
            session.close()
            print(f"Embeddings cache loaded for {len(self.embeddings_cache)} categories")
            
            for cache_key, embeddings in self.embeddings_cache.items():
                print(f"  - {cache_key}: {len(embeddings)} embeddings")
                
        except Exception as e:
            print(f"Error loading embeddings cache: {e}")

    def _sanitize_name(self, name: str) -> str:
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"item_{sanitized}"
        return (sanitized or "default_item").lower()

    def _get_sql_server_column_type(self, column_name: str, is_tech_column: bool = False) -> Any:
        """Get appropriate SQL Server column type based on column purpose"""
        if is_tech_column:
            return SQLServerBoolean() if self.is_sql_server else Boolean()
        
        if column_name in ['title']:
            return NVARCHAR(500) if self.is_sql_server else String(500)
        elif column_name in ['description']:
            return Text() if self.is_sql_server else Text()
        elif column_name in ['score_1', 'score_2', 'score_3', 'score_4', 'weighted_score', 'percentile']:
            return Integer()
        else:
            return NVARCHAR(500) if self.is_sql_server else String(500)

    def _create_category_model(self, category: str, tech_columns: List[str]) -> Any:
        sanitized_category = self._sanitize_name(category)

        if sanitized_category in self.category_models:
            return self.category_models[sanitized_category]

        with _model_lock:
            if sanitized_category in _model_cache:
                model_class = _model_cache[sanitized_category]
            else:
                base_model = WorkExperience if self.is_workex_db else Project
                
                attrs = {
                    '__tablename__': sanitized_category,
                    'id': Column(Integer, primary_key=True, autoincrement=True),
                }
                
                for tech in tech_columns:
                    sanitized_tech = self._sanitize_name(tech)
                    attrs[sanitized_tech] = Column(
                        self._get_sql_server_column_type(sanitized_tech, is_tech_column=True), 
                        default=False, 
                        nullable=True
                    )
                
                attrs['__table_args__'] = {'extend_existing': True}

                model_class = type(f'{sanitized_category}Model', (base_model,), attrs)
                _model_cache[sanitized_category] = model_class
        
        self.category_models[sanitized_category] = model_class
        return model_class

    def _load_prompt(self, filename: str) -> str:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: Prompt file {filename} not found. Using default prompt.")
            return "Please analyze this project and provide a score."

    def _get_scoring_prompt(self, category: str) -> str:
        category_lower = category.lower()
        if category_lower == 'design':
            return self.scoring_prompts['design']
        elif category_lower in ['consult', 'finance', 'strategy']:
            return self.scoring_prompts['non_tech']
        else:
            return self.scoring_prompts['default']

    def _json_parser(self, project_json: Dict) -> Tuple[str, str]:
        title = project_json.get('title', 'Untitled Project')
        
        if self.is_workex_db:
            description = project_json.get('responsibilities', '') or ''
        else:
            description = project_json.get('description', '') or ''
        
        key_points = ' '.join(project_json.get('key_points', []))
        total_description = f"{description}\n{key_points}".strip()
        return title, total_description

    def _get_response_with_key(self, prompt: str, key_index: int, max_retries: int = 3) -> str:
        """
        Enhanced method that cycles through all available API keys when rate limited.
        Only abandons project if ALL keys are exhausted.
        """
        keys_tried = set()
        current_key_index = key_index
        
        while len(keys_tried) < len(self.api_keys):
            current_key_index = current_key_index % len(self.api_keys)
            keys_tried.add(current_key_index)
            
            self.key_semaphores[current_key_index].acquire()
            
            try:
                for attempt in range(max_retries):
                    try:
                        response = self.clients[current_key_index].chat.completions.create(
                            model="qwen-3-235b-a22b-instruct-2507",
                            messages=[{"role": "user", "content": prompt}],
                            seed=42
                        )
                        
                        with self.stats_lock:
                            self.request_count += 1
                            self.requests_per_key[current_key_index] += 1
                        
                        return response.choices[0].message.content.strip()
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        
                        if 'rate limit' in error_msg or 'too many requests' in error_msg or '429' in error_msg:
                            print(f"Rate limit hit for key {current_key_index + 1}, trying next key...")
                            
                            # If this is the last retry for this key, break to try next key
                            if attempt == max_retries - 1:
                                break
                            
                            # Wait before retrying with same key
                            wait_time = 2 ** attempt
                            time.sleep(wait_time)
                            continue
                        else:
                            # Non-rate-limit error
                            if attempt == max_retries - 1:
                                print(f"Non-rate-limit error with key {current_key_index + 1}: {e}")
                                break
                            time.sleep(1)
                            continue
            
            finally:
                self.key_semaphores[current_key_index].release()
            
            # Move to next key if current one failed
            current_key_index = (current_key_index + 1) % len(self.api_keys)
        
        # Only raise exception if ALL keys failed
        raise Exception(f"All {len(self.api_keys)} API keys have been exhausted or are rate limited")


    def _get_response_parallel(self, prompt: str) -> str:
        with self.stats_lock:
            min_usage_key = min(self.requests_per_key, key=self.requests_per_key.get)
        
        return self._get_response_with_key(prompt, min_usage_key)

    def _get_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="qwen-3-235b-a22b-instruct-2507",
            messages=[{"role": "user", "content": prompt}],
            seed=42
        )
        return response.choices[0].message.content.strip()

    def _convert_boolean_for_sqlserver(self, value) -> Any:
        """Convert boolean values appropriately for SQL Server BIT columns"""
        if value is None:
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            return 1 if value == '1' or value.lower() == 'true' else 0
        if isinstance(value, (int, float)):
            return 1 if value else 0
        return 0

    def _parse_score(self, score_str):
        """Parse score string and return integer or None"""
        if not score_str:
            return None
        
        # Remove any whitespace
        score_str = str(score_str).strip()
        
        # Check if it's a valid number (integer or float)
        try:
            score_float = float(score_str)
            # Ensure score is within valid range (1-10)
            if 1 <= score_float <= 10:
                return int(round(score_float))  # Round to nearest integer
            else:
                print(f"Warning: Score {score_float} out of range (1-10), setting to None")
                return None
        except (ValueError, TypeError):
            print(f"Warning: Invalid score format '{score_str}', setting to None")
            return None

    def _is_valid_score(self, score_str):
        """Check if score string is a valid number in range 1-10"""
        if not score_str:
            return False
        try:
            score = float(str(score_str).strip())
            return 1 <= score <= 10
        except (ValueError, TypeError):
            return False

    def _process_single_project(self, project_data: Tuple[int, pd.Series, str, List[str]]) -> Dict:
        idx, row, category, tech_list = project_data
        
        try:
            project_json = json.loads(row['experience'])
            title, description = self._json_parser(project_json)
            
            # FIXED: Ensure complete prompt construction
            scoring_prompt_template = self._get_scoring_prompt(category)
            
            # Construct the full scoring prompt with project details
            full_scoring_prompt = f"{scoring_prompt_template}\n\nPROJECT INPUT: {title}\n\n{description}"
            
            # Construct tagging prompt
            skills_list_str = '\n'.join(tech_list)
            tagging_prompt_formatted = self.tagging_prompt.replace("SKILLS LIST:", f"SKILLS LIST: {skills_list_str}")
            full_tagging_prompt = f"{tagging_prompt_formatted}\n\nTitle: {title}\nDescription: {description}"

            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                score_future = executor.submit(self._get_response_parallel, full_scoring_prompt)
                tag_future = executor.submit(self._get_response_parallel, full_tagging_prompt)
                
                score_response = score_future.result().strip()
                tag_response = tag_future.result()
            
            
            # IMPROVED: Better parsing of score response with validation
            scores = []
            if score_response and not any(word in score_response.lower() for word in ['please', 'provide', 'project', 'missing']):
                # Split by spaces and filter out empty strings
                score_parts = [part.strip() for part in score_response.split() if part.strip()]
                
                # Look for numeric values in the response
                numeric_parts = []
                for part in score_parts:
                    try:
                        # Try to extract numeric value
                        if '.' in part:
                            num = float(part)
                        else:
                            num = int(part)
                        
                        if 1 <= num <= 10:
                            numeric_parts.append(str(int(round(num))))
                    except ValueError:
                        continue
                
                if len(numeric_parts) >= 4:
                    scores = numeric_parts[:4]
                elif len(numeric_parts) > 0:
                    # If we have some scores but not 4, repeat the available ones
                    scores = (numeric_parts * 4)[:4]
                else:
                    print(f"Error: No valid numeric scores found in response: {score_response}")
                    scores = ['', '', '', '']
            else:
                print(f"Error: Invalid AI response received: {score_response}")
                # Return empty scores to trigger fallback handling
                scores = ['', '', '', '']
            
            # Process tags
            used_skills = [skill.strip() for skill in tag_response.split('\n') if skill.strip()]
            tags = []
            for skill in tech_list:
                tags.append('1' if skill in used_skills else '0')
            
            # Calculate weighted score from valid numeric scores
            numeric_scores = []
            for score_str in scores:
                if self._is_valid_score(score_str):
                    numeric_scores.append(float(score_str))
            
            # Calculate weighted score
            if numeric_scores:
                weighted_score = int(round(sum(numeric_scores) / len(numeric_scores) * 10))
            else:
                weighted_score = 0
                print(f"Warning: No valid numeric scores found for project '{title}'. Scores received: {scores}")
            
            return {
                'success': True,
                'idx': idx,
                'title': title,
                'description': description,
                'scores': scores,
                'tags': tags,
                'weighted_score': weighted_score,
                'tech_list': tech_list
            }
            
        except Exception as e:
            print(f"Error processing project {idx}: {str(e)}")
            return {
                'success': False,
                'idx': idx,
                'error': str(e)
            }


    def _batch_process_projects(self, projects_data: List[Tuple], batch_size: int = 20) -> List[Dict]:
        results = []
        
        for i in range(0, len(projects_data), batch_size):
            batch = projects_data[i:i+batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(self._process_single_project, batch))
                results.extend(batch_results)
            
            time.sleep(1)
        
        return results

    def make_db_concurrent(self, csv_file: str, category: str, out_dir: str, make_csv: bool, display_output: bool = True):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            tech_file_path = os.path.join(script_dir, 'TechStack', f'{category}_technologies.txt')
            with open(tech_file_path, 'r', encoding='utf-8') as file:
                technologies = file.read().strip()
            tech_list = technologies.split('\n')
            if tech_list == ['']:
                tech_list = []
        except FileNotFoundError:
            return
        
        model = self._create_category_model(category, tech_list)
        self.Base.metadata.create_all(self.engine)
        
        df = pd.read_csv(csv_file)
        category_df = df[df['classification'] == category]
        
        projects_data = []
        for idx, (_, row) in enumerate(category_df.iterrows()):
            projects_data.append((idx, row, category, tech_list))
        
        results = self._batch_process_projects(projects_data)
        
        session = self.session_factory()
        successful_count = 0
        failed_count = 0
        
        try:
            for result in results:
                if result['success']:
                    # FIXED: Properly handle score parsing and validation
                    scores = result['scores']
                    
                    # Parse each score with validation
                    score_1 = self._parse_score(scores[0]) if len(scores) > 0 else None
                    score_2 = self._parse_score(scores[1]) if len(scores) > 1 else None
                    score_3 = self._parse_score(scores[2]) if len(scores) > 2 else None
                    score_4 = self._parse_score(scores[3]) if len(scores) > 3 else None
                    
                    # Calculate weighted score only from valid scores
                    valid_scores = [s for s in [score_1, score_2, score_3, score_4] if s is not None]
                    
                    if valid_scores:
                        # Use average of valid scores * 10 for weighted score
                        weighted_score = int(round(sum(valid_scores) / len(valid_scores) * 10))
                    else:
                        # If no valid scores, set weighted score to 0
                        weighted_score = 0
                        print(f"Warning: No valid scores found for project '{result['title']}', setting weighted_score to 0")

                    project_instance = model(
                        title=result['title'],
                        description=result['description'],
                        score_1=score_1,  # Now properly validated
                        score_2=score_2,  # Now properly validated  
                        score_3=score_3,  # Now properly validated
                        score_4=score_4,  # Now properly validated
                        weighted_score=weighted_score  # Now properly calculated
                    )
                    
                    # Set technology columns with proper boolean conversion for SQL Server
                    for i, tech in enumerate(result['tech_list']):
                        sanitized_tech = self._sanitize_name(tech)
                        if hasattr(project_instance, sanitized_tech) and i < len(result['tags']):
                            bool_value = result['tags'][i] == '1'
                            if self.is_sql_server:
                                setattr(project_instance, sanitized_tech, bool_value)
                            else:
                                setattr(project_instance, sanitized_tech, bool_value)
                    
                    session.add(project_instance)
                    successful_count += 1
                    
                else:
                    failed_count += 1
            
            session.commit()
            
            # Calculate percentiles AFTER all projects are added
            self._add_percentiles_to_model(category)
            
            if make_csv:
                os.makedirs(out_dir, exist_ok=True)
                projects = session.query(model).all()
                data = []
                for project in projects:
                    row = {
                        'Title': project.title,
                        'Description': project.description,
                        'Score_1': project.score_1,
                        'Score_2': project.score_2,
                        'Score_3': project.score_3,
                        'Score_4': project.score_4,
                        'Weighted_Score': project.weighted_score,
                        'Percentile': project.percentile  # Include percentile in CSV
                    }
                    for tech in tech_list:
                        sanitized_tech = self._sanitize_name(tech)
                        if hasattr(project, sanitized_tech):
                            row[tech] = getattr(project, sanitized_tech)
                    data.append(row)
                
                pd.DataFrame(data).to_csv(f'{out_dir}/{category}_complete.csv', index=False)
        
        except Exception as e:
            session.rollback()
            raise e
        
        finally:
            session.close()

    def _calculate_percentile(self, final_score: int, category: str) -> int:
        sanitized_category = self._sanitize_name(category)
        
        if sanitized_category not in self.category_models:
            return 0
        
        try:
            model = self.category_models[sanitized_category]
            session = self.session_factory()
            
            scores = session.query(model.weighted_score).filter(
                model.weighted_score.isnot(None)
            ).all()
            
            if not scores:
                session.close()
                return 0
            
            scores_array = np.array([score[0] for score in scores])
            scores_below = np.sum(scores_array < final_score)
            scores_equal = np.sum(scores_array == final_score)
            
            percentile = ((scores_below + 0.5 * scores_equal) / len(scores_array)) * 100
            session.close()
            return round(percentile)
            
        except SQLAlchemyError as e:
            return 0

    def get_percentile_for_score(self, score: int, category: str) -> int:
        return self._calculate_percentile(score, category)

    def _add_percentiles_to_model(self, category: str):
        """Calculate and update percentiles for all projects in a category"""
        sanitized_category = self._sanitize_name(category)
        
        if sanitized_category not in self.category_models:
            return
        
        try:
            model = self.category_models[sanitized_category]
            session = self.session_factory()
            
            # Get all projects with non-null weighted scores
            projects = session.query(model).filter(
                model.weighted_score.isnot(None),
                model.weighted_score > 0  # Exclude 0 scores from percentile calculation
            ).all()
            
            if not projects:
                print(f"Warning: No valid projects found for percentile calculation in category '{category}'")
                session.close()
                return
            
            # Calculate percentiles
            scores = [project.weighted_score for project in projects]
            sorted_scores = sorted(scores)
            
            # Update percentiles for all projects
            all_projects = session.query(model).all()
            
            for project in all_projects:
                if project.weighted_score is None or project.weighted_score == 0:
                    project.percentile = 0  # Set percentile to 0 for invalid scores
                else:
                    # Calculate percentile ranking
                    rank = sorted_scores.index(project.weighted_score) + 1
                    percentile = round((rank / len(sorted_scores)) * 100)
                    project.percentile = percentile
            
            session.commit()
            print(f"✅ Updated percentiles for {len(all_projects)} projects in category '{category}'")
            session.close()
            
        except Exception as e:
            print(f"Error calculating percentiles for category '{category}': {e}")
            if 'session' in locals():
                session.rollback()
                session.close()

    def finalize_database(self):
        for category in self.category_models.keys():
            self._add_percentiles_to_model(category)

    def score_project(self, project_json: Dict, category: str, display_output: bool = True) -> List[str]:
        title, total_description = self._json_parser(project_json)
        scoring_prompt = self._get_scoring_prompt(category)
        full_prompt = f"{scoring_prompt}\n\nTitle: {title}\nDescription: {total_description}"
        
        if len(self.api_keys) > 1:
            response_text = self._get_response_parallel(full_prompt).split(' ')
        else:
            response_text = self._get_response(full_prompt).split(' ')

        if display_output:
            self._print_scores(title, response_text)
        
        return response_text

    def tag_project(self, project_json: Dict, tech_list: List[str], display_output: bool = True) -> List[str]:
        title, description = self._json_parser(project_json)
        skills_list_str = '\n'.join(tech_list)
        prompt = self.tagging_prompt.replace("SKILLS LIST:", f"SKILLS LIST: {skills_list_str}")
        full_prompt = f"{prompt}\n\nTitle: {title}\nDescription: {description}"
        
        if len(self.api_keys) > 1:
            response_text = self._get_response_parallel(full_prompt)
        else:
            response_text = self._get_response(full_prompt)
        
        used_skills = [skill.strip() for skill in response_text.split('\n') if skill.strip()]
        
        scores = []
        for skill in tech_list:
            if skill in used_skills:
                scores.append('1')
            else:
                scores.append('0')
        
        if display_output:
            print(f"Title: {title}")
            print(f"Description: {description}")
            print(f"Used skills: {', '.join(used_skills)}")
            print(f"Scores: {' '.join(scores)}")
            print()
        
        return scores


    def suggest_projects_with_gemini(self, user_projects_by_category: dict, similar_projects_by_category: dict) -> dict:
        if not self.gemini_model:
            return {"error": "Gemini API not configured"}
        
        suggestions_by_category = {}
        
        for category, category_data in user_projects_by_category.items():
            try:
                if 'error' in category_data and category_data['error'] is not None:
                    suggestions_by_category[category] = {
                        'category': category,
                        'error': category_data['error']
                    }
                    continue

                user_projects = category_data.get('project_details', [])
                similar_projects = category_data.get('similar_projects', [])
                technologies_used = category_data.get('combined_technologies_used', [])
                
                if not user_projects:
                    continue
                
                prompt = self._create_project_suggestion_prompt(
                    category=category,
                    user_projects=user_projects,
                    similar_projects=similar_projects,
                    technologies_used=technologies_used
                )
                
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        response_mime_type="application/json"
                    ),
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    }
                )
                
                try:
                    suggestions_json = json.loads(response.text)
                    
                    suggestions_by_category[category] = {
                        'category': category,
                        'user_projects_count': len(user_projects),
                        'similar_projects_count': len(similar_projects),
                        'technologies_used': technologies_used,
                        'average_score': category_data.get('average_score', 0),
                        'suggested_projects': suggestions_json.get('suggested_projects', []),
                        'skill_gap_analysis': suggestions_json.get('skill_gap_analysis', {}),
                        'learning_path': suggestions_json.get('learning_path', []),
                        'portfolio_recommendations': suggestions_json.get('portfolio_recommendations', {})
                    }
                    
                except json.JSONDecodeError as e:
                    suggestions_by_category[category] = {
                        'category': category,
                        'error': f"Failed to parse AI response: {str(e)}",
                        'raw_response': response.text
                    }
                    
            except Exception as e:
                suggestions_by_category[category] = {
                    'category': category,
                    'error': f"Failed to generate suggestions: {str(e)}"
                }
        
        return suggestions_by_category

    def get_project_improvements_with_gemini(self, user_project: dict, similar_projects: list, category: str) -> dict:
        if not self.gemini_model:
            return {"error": "Gemini API not configured"}

        try:
            prompt = self._create_project_improvement_prompt(
                user_project=user_project,
                similar_projects=similar_projects,
                category=category
            )

            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.8,
                    response_mime_type="application/json"
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )

            try:
                improvements_json = json.loads(response.text)
                return improvements_json
            except json.JSONDecodeError as e:
                return {
                    'error': f"Failed to parse AI response: {str(e)}",
                    'raw_response': response.text
                }

        except Exception as e:
            return {
                'error': f"Failed to generate improvements: {str(e)}"
            }

    def _create_project_suggestion_prompt(self, category: str, user_projects: list, similar_projects: list, technologies_used: list) -> str:
        prompt = f"""
# Project Portfolio Enhancement Analysis for {category} Domain

## Context
You are an expert technical mentor and career advisor specializing in {category}. Analyze the user's current projects and provide actionable recommendations for portfolio enhancement.

## User's Current Projects Analysis:
"""
        
        for i, project in enumerate(user_projects, 1):
            prompt += f"""
### Project {i}: {project.get('title', 'Untitled')}
- **Description:** {project.get('description', 'No description')[:400]}...
- **Score:** {project.get('score', 0)}/100
- **Technologies Used:** {', '.join(project.get('technologies_used', [])[:8])}
"""
        
        prompt += f"""

## User's Technology Stack:
**Current Technologies:** {', '.join(technologies_used[:15]) if technologies_used else 'None identified'}

## Industry Benchmark Projects (High-Performing References):
"""
        
        for i, similar_proj in enumerate(similar_projects[:3], 1):
            if isinstance(similar_proj, (list, tuple)) and len(similar_proj) >= 2:
                title = similar_proj[0] if similar_proj else "Unknown Project"
                description = similar_proj[1] if similar_proj[1] else "No description"
                percentile = similar_proj if len(similar_proj) > 2 else "Unknown"
                
                prompt += f"""
### Benchmark {i}: {title}
- **Description:** {description[:300]}...
- **Performance Percentile:** {percentile}
"""
        
        prompt += f"""

## Task Requirements:
Generate exactly 4-5 project suggestions that strategically enhance the user's {category} portfolio. Focus on:

1. **Progressive Skill Building** - Each project should introduce 1-2 new technologies
2. **Market Relevance** - Align with current {category} industry demands
3. **Portfolio Impact** - Projects that demonstrate growth and expertise
4. **Technical Depth** - Increasing complexity that showcases advanced skills

## Required JSON Output Format:
Please respond with ONLY a valid JSON object in this exact structure:

{{
"suggested_projects": [
{{
"project_title": "Specific, compelling project name",
"difficulty_level": "Beginner|Intermediate|Advanced",
"estimated_duration": "Time estimate (e.g., '4-6 weeks', '2-3 months')",
"primary_technologies": ["tech1", "tech2", "tech3"],
"new_technologies_to_learn": ["new_tech1", "new_tech2"],
"project_description": "Detailed description of what to build (200-300 words)",
"key_features": ["feature1", "feature2", "feature3", "feature4"],
"learning_objectives": ["objective1", "objective2", "objective3"],
"industry_relevance": "Why this project matters in current market",
"portfolio_impact": "How this enhances the overall portfolio",
"implementation_phases": [
"Phase 1: Basic implementation",
"Phase 2: Advanced features",
"Phase 3: Optimization/deployment"
],
"success_metrics": ["measurable outcome 1", "measurable outcome 2"]
}}
],
"skill_gap_analysis": {{
"current_strengths": ["strength1", "strength2", "strength3"],
"identified_gaps": ["gap1", "gap2", "gap3"],
"priority_skills_to_develop": ["skill1", "skill2", "skill3"],
"market_demand_alignment": "Assessment of how current skills match market needs"
}},
"learning_path": [
{{
"phase": "Phase 1: Foundation",
"duration": "1-2 months",
"focus_areas": ["area1", "area2"],
"recommended_resources": ["resource1", "resource2"]
}},
{{
"phase": "Phase 2: Intermediate",
"duration": "2-3 months",
"focus_areas": ["area1", "area2"],
"recommended_resources": ["resource1", "resource2"]
}},
{{
"phase": "Phase 3: Advanced",
"duration": "2-4 months",
"focus_areas": ["area1", "area2"],
"recommended_resources": ["resource1", "resource2"]
}}
],
"portfolio_recommendations": {{
"prioritization_order": [],
"showcase_strategy": "How to present these projects effectively",
"github_organization": "Tips for organizing code repositories",
"documentation_focus": "Key areas to document thoroughly",
"demo_preparation": "How to prepare compelling project demonstrations"
}}
}}

## Guidelines:
- Make suggestions specific to {category} domain
- Consider current industry trends and hiring demands
- Ensure projects build upon each other logically
- Include both technical and soft skill development
- Focus on projects that can be completed individually
- Provide actionable, specific guidance throughout

Return ONLY the JSON object with no additional text or formatting.
"""
        
        return prompt

    def _create_project_improvement_prompt(self, user_project: dict, similar_projects: list, category: str) -> str:
        prompt = f"""
    # Project Enhancement Analysis for {category} Domain
    
    ## Your Current Project:
    ### Title: {user_project.get('title', 'Untitled')}
    - **Description:** {user_project.get('description', 'No description')}
    - **Technologies Used:** {', '.join(user_project.get('technologies_used', []))}
    
    ## Reference Projects (Industry Examples):
    """
        for i, similar_proj in enumerate(similar_projects[:3], 1):
            if isinstance(similar_proj, (list, tuple)) and len(similar_proj) >= 2:
                title = similar_proj[0]
                description = similar_proj[1]
                prompt += f"""
    ### Reference {i}: {title}
    - **Description:** {description}
    """
        
        prompt += """
    ## Analysis Task:
    You are a technical resume expert specializing in ATS optimization. Your goal is to enhance the user's existing project description to make it more impactful for recruiters and ATS systems, while staying true to the original project scope.
    
    ### Critical Guidelines:
    - **Stay faithful to the original project**: Only enhance what already exists - do not add features, capabilities, or technologies that aren't in the user's description
    - **Preserve technical accuracy**: Do not exaggerate or misrepresent the project's actual functionality
    - **Focus on articulation**: Improve how the project is described, not what the project does
    - **ATS optimization**: Incorporate relevant industry keywords and quantifiable metrics where the original description implies them
    - **Use reference projects** only as inspiration for phrasing and presentation style, not for adding new features
    
    ### Enhancement Focus Areas:
    1. **Rewrite bullet points** with action verbs, quantifiable results (if implied), and industry-standard terminology
    2. **Add ATS-friendly keywords** that match the existing technologies and methodologies used
    3. **Suggest presentation improvements** for better readability and impact
    4. **Recommend complementary technologies** only if they naturally extend what's already built
    
    ### Enhanced Bullet Points Requirements:
    - Start with strong action verbs (Developed, Engineered, Implemented, Architected, Optimized, etc.)
    - Include specific technical details already present in the original description
    - Add measurable outcomes where logically implied (performance improvements, scalability, user impact)
    - Use industry-standard terminology and keywords relevant to the {category} domain
    - Maintain 3-5 bullet points that accurately reflect the original project scope
    
    ## Required JSON Output Format:
    Respond with ONLY a valid JSON object in this exact structure:
    
    {{
      "project_title": "Original Project Title",
      "improvements": {{
        "enhanced_bullet_points": [
            "Action-oriented bullet point 1 with quantifiable impact and ATS keywords.",
            "Action-oriented bullet point 2 emphasizing technical depth and achievements.",
            "Action-oriented bullet point 3 highlighting scalability, efficiency, or user value."
        ],
        "key_improvements": [
          "Specific enhancement to make the description more compelling without changing project scope.",
          "Recommendation for better articulation of existing technical implementations.",
          "Suggestion for highlighting measurable impact or technical sophistication already present."
        ],
        "suggested_technologies": [
          {{
            "name": "Technology Name",
            "reason": "Why this naturally complements the existing technology stack and project goals."
          }},
          {{
            "name": "Another Technology",
            "reason": "How this would enhance or extend current functionality without major deviations."
          }}
        ]
      }}
    }}
    
    IMPORTANT: Return ONLY the JSON object with no additional text, markdown formatting, or explanations.
    """
        return prompt

    def get_similar_projects(self, category: str, score: int, tags: List[str], limit: int = 5):
        """Get top N projects with similar scores and matching tech stack"""
        sanitized_category = self._sanitize_name(category)
        df = None
        
        if sanitized_category in self.category_models:
            try:
                model = self.category_models[sanitized_category]
                session = self.session_factory()
                
                projects = session.query(model).filter(model.weighted_score.isnot(None)).all()
                
                if not projects:
                    session.close()
                    return []
                
                data = []
                for project in projects:
                    row = {
                        'Title': project.title,
                        'Description': project.description,
                        'Percentile': project.percentile,
                        'Score_1': project.score_1,
                        'Score_2': project.score_2,
                        'Score_3': project.score_3,
                        'Score_4': project.score_4,
                        'Weighted_Score': project.weighted_score
                    }
                    # Get technology columns (boolean/BIT columns)
                    for column in model.__table__.columns:
                        if column.name not in ['id', 'title', 'description', 'score_1', 'score_2', 'score_3', 'score_4', 'weighted_score', 'percentile']:
                            value = getattr(project, column.name)
                            # Convert SQL Server BIT values to Python boolean for consistency
                            if self.is_sql_server and value is not None:
                                row[column.name] = bool(value)
                            else:
                                row[column.name] = value
                    data.append(row)
                
                df = pd.DataFrame(data)
                session.close()
                
            except Exception as e:
                df = None
        
        if df is None:
            return []
        
        score_col = None
        if 'Weighted_Score' in df.columns:
            score_col = 'Weighted_Score'
        elif 'weighted_score' in df.columns:
            score_col = 'weighted_score'
        else:
            return []
        
        df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
        df = df.dropna(subset=[score_col])
        
        if len(df) == 0:
            return []
        
        # Identify technology columns (exclude standard columns and embedding)
        non_tech_cols = ['Title', 'title', 'Description', 'description', 'Company', 'company', 
                        'Score_1', 'score_1', 'Score_2', 'score_2', 'Score_3', 'score_3', 
                        'Score_4', 'score_4', 'Weighted_Score', 'weighted_score', 
                        'Percentile', 'percentile', 'id', 'embedding']
        tech_cols = [col for col in df.columns if col not in non_tech_cols]
        
        if not tech_cols:
            return []
        
        input_tags = np.array([int(tag) for tag in tags[:len(tech_cols)]])
        
        similar_projects = []
        for _, row in df.iterrows():
            try:
                # Handle boolean values from SQL Server BIT columns
                project_tags = []
                for col in tech_cols:
                    value = row[col]
                    if pd.isna(value):
                        project_tags.append(0)
                    elif isinstance(value, bool):
                        project_tags.append(1 if value else 0)
                    else:
                        project_tags.append(int(value) if value else 0)
                
                project_tags = np.array(project_tags)
                project_score = int(row[score_col])
                
                score_difference = abs(project_score - score)
                
                dot_product = np.dot(input_tags, project_tags)
                norm_input = np.linalg.norm(input_tags)
                norm_project = np.linalg.norm(project_tags)
                
                if norm_input == 0 or norm_project == 0:
                    cos_similarity = 0.0
                else:
                    cos_similarity = dot_product / (norm_input * norm_project)
                
                if cos_similarity >= 0.1:
                    title = row.get('Title', row.get('title', 'Unknown Title'))
                    description = row.get('Description', row.get('description', 'No description'))
                    percentile = row.get('Percentile', row.get('percentile', 0))
                    
                    similar_projects.append({
                        'title': title,
                        'description': description,
                        'percentile': int(percentile) if percentile else 0,
                        'weighted_score': project_score,
                        'score_difference': score_difference,
                        'cosine_similarity': round(cos_similarity, 3),
                        'technology_match': project_tags.tolist()
                    })
                    
            except Exception as e:
                continue
        
        if not similar_projects:
            return []
        
        similar_projects.sort(key=lambda x: (x['score_difference'], -x['cosine_similarity']))
        
        top_projects = similar_projects[:limit]
        
        result = []
        for project in top_projects:
            result.append((
                project['title'],
                project['description'], 
                project['percentile'],
                project['cosine_similarity']
            ))
        
        return result

    def analyze_project(self, project_json: Dict, category: str, scores_range: int, similarity: float, latest: bool = False):
        """Analyze a project and find similar projects (enhanced for both database types)"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tech_file_path = os.path.join(script_dir, 'TechStack', f'{category}_technologies.txt')
            
            if not os.path.exists(tech_file_path):
                tech_file_path = f'TechStack/{category}_technologies.txt'
                
            if not os.path.exists(tech_file_path):
                return 0, [], []
            
            with open(tech_file_path, 'r', encoding='utf-8') as file:
                technologies = file.read().strip()
            
            tech_list = technologies.split('\n')
            if tech_list == ['']:
                tech_list = []
                
        except Exception as e:
            return 0, [], []
        
        try:
            scores = self.score_project(project_json, category, False)
            
            tags = self.tag_project(project_json, tech_list, False)
            used_techs = [tech_list[i] for i, tag in enumerate(tags) if tag == '1']
            
            numeric_scores = [int(x) for x in scores if x.isdigit()]
            if not numeric_scores:
                return 0, used_techs, []
                
            final_score = round(sum(numeric_scores) * 2.5)
            percentile = self._calculate_percentile(final_score, category)
            
            # Find similar projects - use latest version if requested
            if latest:
                # Extract description from project_json for semantic search
                title = project_json.get('title', '')
                description = project_json.get('description', '')
                
                similar_projects = self.get_similar_projects_v2(title, description, category)
            else:
                similar_projects = self.get_similar_projects(category, percentile, tags)
            
            return percentile, used_techs, similar_projects
            
        except Exception as e:
            return 0, [], []

    def get_database_info(self) -> Dict:
        try:
            info = {}
            
            for category, model in self.category_models.items():
                session = self.session_factory()
                count = session.query(model).count()
                columns = [column.name for column in model.__table__.columns]
                
                info[category] = {
                    'row_count': count,
                    'columns': columns,
                    'model': model.__name__
                }
                session.close()
            
            return info
        except SQLAlchemyError as e:
            return {}

    def _print_scores(self, title: str, scores: List[str]):
        """Print formatted scores for debugging"""
        print(f"Project: {title}")
        print(f"Scores: {' '.join(scores)}")
        print("-" * 50)

    def print_api_usage_summary(self):
        print("\n" + "="*50)
        print("API USAGE SUMMARY")
        print("="*50)
        print(f"Total requests made: {self.request_count}")
        for i, count in self.requests_per_key.items():
            print(f"API Key #{i + 1}: {count} requests")
        print(f"Average requests per key: {self.request_count / len(self.api_keys):.1f}")
        print("="*50)

    def close_connections(self):
        """Close database connections and cleanup resources"""
        try:
            self.engine.dispose()
            # Clear embeddings cache to free memory
            if hasattr(self, 'embeddings_cache'):
                self.embeddings_cache.clear()
        except SQLAlchemyError as e:
            print(f"Error closing connections: {e}")

    def get_similar_projects_v2(self, title: str, description: str, category: str, top_k: int = 5) -> List[Tuple[str, str, int, float]]:
        """Find similar projects using semantic embeddings (SQL Server version)."""
        if not EMBEDDING_SUPPORT or not self.sentence_model:
            print("Embedding functionality not available")
            return []
            
        try:
            # Sanitize category name
            sanitized_category = self._sanitize_name(category)
            
            # Determine database prefix
            db_prefix = 'workex' if self.is_workex_db else 'projects'
            cache_key = f"{db_prefix}_{sanitized_category}"
            
            print(f"Looking for cache key: {cache_key}")
            print(f"Available cache keys: {list(self.embeddings_cache.keys())}")
            
            # Check if we have embeddings for this category
            if cache_key not in self.embeddings_cache:
                print(f"No embeddings found for category '{category}' in {db_prefix} database")
                print(f"Cache key '{cache_key}' not found in cache")
                return []
            
            cached_embeddings = self.embeddings_cache[cache_key]
            
            if len(cached_embeddings) == 0:
                print(f"No embeddings available for category '{category}'")
                return []
            
            print(f"Found {len(cached_embeddings)} cached embeddings for {category}")
            
            # Generate embedding for input description
            query_embedding = self.sentence_model.encode([title+" "+description])
            
            # Compute cosine similarities
            similarities = cosine_similarity(query_embedding, cached_embeddings)[0]
            
            # Get top-k most similar projects
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Query database for project details
            results = []
            try:
                session = self.session_factory()
                
                # Get projects by row number (using OFFSET/FETCH for SQL Server)
                result = session.execute(text(f"""
                    SELECT title, description, percentile 
                    FROM [{sanitized_category}] 
                    WHERE embedding IS NOT NULL AND LEN(embedding) > 0
                    ORDER BY id
                """))
                
                all_projects = result.fetchall()
                session.close()
                
                for idx in top_indices:
                    if idx < len(all_projects) and similarities[idx] >= 0.1:
                        title, desc, percentile = all_projects[idx]
                        similarity_score = float(similarities[idx])
                        
                        results.append((
                            title,
                            desc,
                            int(percentile) if percentile else 0,
                            similarity_score
                        ))
                
                print(f"Returning {len(results)} similar projects")
                return results
                
            except Exception as e:
                print(f"Error fetching project data: {e}")
                return []
            
        except Exception as e:
            print(f"Error in get_similar_projects_v2: {e}")
            return []

    def get_tech_list(self, category: str) -> List[str]:
        """Loads the technologies for a given category."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            tech_file_path = os.path.join(script_dir, 'TechStack', f'{category}_technologies.txt')
            with open(tech_file_path, 'r', encoding='utf-8') as file:
                technologies = file.read().strip()
            tech_list = technologies.split('\n')
            if tech_list == ['']:
                return []
            return tech_list
        except FileNotFoundError:
            return []

    def project_exists(self, project_json: Dict, category: str, new_project_tags: List[str], similarity_threshold: float = 0.95) -> bool:
        """Checks if a project already exists in the database by title and tags, or by description similarity."""
        sanitized_category = self._sanitize_name(category)
        if sanitized_category not in self.category_models:
            return False

        title, description = self._json_parser(project_json)
        model = self.category_models[sanitized_category]
        session = self.session_factory()

        # 1. Check for items with the same title
        existing_items = session.query(model).filter_by(title=title).all()
        if existing_items:
            tech_list = self.get_tech_list(category)
            # If tags are provided, compare them
            if new_project_tags and tech_list:
                for item in existing_items:
                    existing_tags = []
                    for tech in tech_list:
                        sanitized_tech = self._sanitize_name(tech)
                        existing_tags.append('1' if getattr(item, sanitized_tech, False) else '0')
                    
                    if existing_tags == new_project_tags:
                        session.close()
                        return True
            else: # If no tags, title match is sufficient
                session.close()
                return True

        # 2. Check for description similarity as a fallback
        if not EMBEDDING_SUPPORT or not self.sentence_model or not description:
            session.close()
            return False
            
        db_prefix = 'workex' if self.is_workex_db else 'projects'
        cache_key = f"{db_prefix}_{sanitized_category}"
        
        if cache_key not in self.embeddings_cache or len(self.embeddings_cache[cache_key]) == 0:
            session.close()
            return False
            
        query_embedding = self.sentence_model.encode([description])
        similarities = cosine_similarity(query_embedding, self.embeddings_cache[cache_key])[0]
        
        session.close()
        
        if np.max(similarities) > similarity_threshold:
            return True
            
        return False

    def add_project(self, project_json: Dict, category: str, scores: Dict, tags: List[str]):
        """Adds a new project to the database."""
        sanitized_category = self._sanitize_name(category)
        tech_list = self.get_tech_list(category)
        if not tech_list:
            return
            
        model = self._create_category_model(category, tech_list)
        self.Base.metadata.create_all(self.engine)
        
        title, description = self._json_parser(project_json)
        
        session = self.session_factory()
        try:
            project_instance = model(
                title=title,
                description=description,
                score_1=scores.get('technical_complexity'),
                score_2=scores.get('technology_stack_relevance'),
                score_3=scores.get('innovation_uniqueness'),
                score_4=scores.get('project_scope_completeness'),
                weighted_score=scores.get('weighted_score'),
                percentile=self._calculate_percentile(scores.get('weighted_score'), category)
            )

            if EMBEDDING_SUPPORT and self.sentence_model:
                embedding = self.sentence_model.encode([description])[0]
                project_instance.embedding = embedding.tobytes()

            for i, tech in enumerate(tech_list):
                sanitized_tech = self._sanitize_name(tech)
                if hasattr(project_instance, sanitized_tech) and i < len(tags):
                    bool_value = tags[i] == '1'
                    setattr(project_instance, sanitized_tech, bool_value)
            
            session.add(project_instance)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
