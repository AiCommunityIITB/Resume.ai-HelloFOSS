import os
import json
import pandas as pd
import numpy as np
from cerebras.cloud.sdk import Cerebras
from sqlalchemy import create_engine, MetaData, Column, Integer, String, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import re
import time
from typing import Dict, List, Optional, Tuple, Any
import concurrent.futures
from threading import Lock
import threading
from dotenv import load_dotenv
import sqlite3

load_dotenv()

Base = declarative_base()

class DesignRetrainer:
    def __init__(self, db_path="projects.db", max_workers=10, max_concurrent_per_key=5):
        # Load multiple API keys
        self.api_keys = [
            os.getenv('CEREBRAS_API_KEY_1'),
            os.getenv('CEREBRAS_API_KEY_2'),
            os.getenv('CEREBRAS_API_KEY_3'),
            os.getenv('CEREBRAS_API_KEY_4')
        ]
        
        # Filter out None values in case some keys aren't set
        self.api_keys = [key for key in self.api_keys if key is not None]
        
        # Fallback to single key if multiple keys not available
        if not self.api_keys:
            single_key = os.getenv('CEREBRAS_API_KEY')
            if single_key:
                self.api_keys = [single_key]
            else:
                raise ValueError("No valid API keys found. Please set CEREBRAS_API_KEY or CEREBRAS_API_KEY_1, CEREBRAS_API_KEY_2, etc.")
        
        print(f"Loaded {len(self.api_keys)} API keys for parallel processing")
        
        # Create multiple clients for concurrent use
        self.clients = [Cerebras(api_key=key) for key in self.api_keys]
        
        # Concurrency settings
        self.max_workers = max_workers
        self.max_concurrent_per_key = max_concurrent_per_key
        
        # Rate limiting and tracking
        self.key_semaphores = [threading.Semaphore(max_concurrent_per_key) for _ in self.api_keys]
        self.request_count = 0
        self.requests_per_key = {i: 0 for i in range(len(self.api_keys))}
        self.stats_lock = Lock()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, db_path)
        
        # Check if we're working with work experience data
        self.is_workex_db = (db_path == "workex.db")
        
        # Create SQLite engine
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=False,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False}
        )
        
        # Create session factory
        Session = sessionmaker(bind=self.engine)
        self.session_factory = Session
        
        # Load the design scoring prompt
        self.design_scoring_prompt = self._load_prompt(os.path.join(script_dir, 'prompts/promptDesign.md'))
        
        # Category to retrain with new prompt
        self.design_category = 'Design'
        
        print(f"Initialized DesignRetrainer for database: {db_path}")
        print(f"Will retrain category: {self.design_category}")
    
    def _load_prompt(self, filename: str) -> str:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize names for use as table/column names"""
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"item_{sanitized}"
        return sanitized or "default_item"
    
    def _json_parser(self, project_json: Dict) -> Tuple[str, str]:
        title = project_json['title']
        
        # Use 'responsibilities' if working with workex.db, otherwise use 'description'
        if self.is_workex_db:
            description = project_json.get('responsibilities', '') or ''
        else:
            description = project_json.get('description', '') or ''
        
        key_points = ' '.join(project_json.get('key_points', []))
        total_description = f"{description}\n{key_points}".strip()
        return title, total_description
    
    def _get_response_with_key(self, prompt: str, key_index: int, max_retries: int = 3) -> str:
        """Get response using a specific API key with semaphore-based rate limiting"""
        
        # Acquire semaphore for this key to limit concurrent requests
        self.key_semaphores[key_index].acquire()
        
        try:
            for attempt in range(max_retries):
                try:
                    response = self.clients[key_index].chat.completions.create(
                        model="qwen-3-235b-a22b-instruct-2507",
                        messages=[{"role": "user", "content": prompt}],
                        seed=42
                    )
                    
                    # Track successful request
                    with self.stats_lock:
                        self.request_count += 1
                        self.requests_per_key[key_index] += 1
                        
                        if self.request_count % 50 == 0:  # Print status every 50 requests
                            print(f"Progress: {self.request_count} requests completed")
                            print(f"Requests per key: {dict(self.requests_per_key)}")
                    
                    return response.choices[0].message.content.strip()
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    if 'rate limit' in error_msg or 'too many requests' in error_msg or '429' in error_msg:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"Rate limit hit for key #{key_index + 1}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        
                        if attempt == max_retries - 1:
                            raise Exception(f"Rate limit exceeded for key {key_index + 1}")
                        continue
                    else:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(1)
                        continue
            
        finally:
            # Always release the semaphore
            self.key_semaphores[key_index].release()
    
    def _get_response_parallel(self, prompt: str) -> str:
        """Get response using load-balanced approach across API keys"""
        # Try keys in round-robin fashion based on current usage
        with self.stats_lock:
            # Find the key with least usage
            min_usage_key = min(self.requests_per_key, key=self.requests_per_key.get)
        
        return self._get_response_with_key(prompt, min_usage_key)
    
    def _get_existing_projects(self, category: str) -> List[Tuple]:
        """Get all existing projects from a category table"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get all data from the category table
            query = f"SELECT * FROM {category}"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            print(f"Found {len(df)} existing projects in {category} table")
            
            # Convert to list of tuples with necessary data
            projects = []
            for idx, row in df.iterrows():
                # Create a project JSON structure from the existing data
                if self.is_workex_db:
                    project_json = {
                        'title': row['title'],
                        'responsibilities': row['description']  # In workex, description contains responsibilities
                    }
                else:
                    project_json = {
                        'title': row['title'],
                        'description': row['description']
                    }
                
                projects.append({
                    'id': row['id'],
                    'project_json': project_json,
                    'original_data': row.to_dict()  # Keep all original data
                })
            
            return projects
            
        except Exception as e:
            print(f"Error getting existing projects for {category}: {e}")
            return []
    
    def _process_single_project(self, project_data: Dict) -> Dict:
        """Process a single project and return the new scores"""
        try:
            project_json = project_data['project_json']
            title, description = self._json_parser(project_json)
            
            # Create scoring prompt with design criteria
            scoring_prompt = f"{self.design_scoring_prompt}\n\nTitle: {title}\nDescription: {description}"
            
            # Get response
            response = self._get_response_parallel(scoring_prompt)
            scores = response.split(' ')
            
            # Calculate weighted score
            numeric_scores = [float(score) for score in scores if score.replace('.', '').isdigit()]
            weighted_score = int(np.mean(numeric_scores) * 10) if numeric_scores else 0
            
            return {
                'success': True,
                'id': project_data['id'],
                'title': title,
                'scores': scores,
                'weighted_score': weighted_score,
                'original_data': project_data['original_data']
            }
            
        except Exception as e:
            return {
                'success': False,
                'id': project_data['id'],
                'error': str(e)
            }
    
    def _batch_process_projects(self, projects_data: List[Dict], batch_size: int = 20) -> List[Dict]:
        """Process projects in batches with controlled concurrency"""
        results = []
        
        for i in range(0, len(projects_data), batch_size):
            batch = projects_data[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(projects_data) + batch_size - 1)//batch_size}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(self._process_single_project, batch))
                results.extend(batch_results)
            
            # Small delay between batches to avoid overwhelming the API
            time.sleep(1)
        
        return results
    
    def _calculate_percentiles(self, category: str, all_scores: List[int]) -> Dict[int, int]:
        """Calculate percentiles for all scores"""
        if not all_scores:
            return {}
        
        sorted_scores = sorted(all_scores)
        percentile_map = {}
        
        for score in all_scores:
            scores_below = sum(1 for s in sorted_scores if s < score)
            scores_equal = sum(1 for s in sorted_scores if s == score)
            percentile = ((scores_below + 0.5 * scores_equal) / len(sorted_scores)) * 100
            percentile_map[score] = round(percentile)
        
        return percentile_map
    
    def _update_database(self, category: str, results: List[Dict]):
        """Update the database with new scores while preserving other data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Collect all weighted scores for percentile calculation
            all_weighted_scores = []
            successful_results = [r for r in results if r['success']]
            
            for result in successful_results:
                all_weighted_scores.append(result['weighted_score'])
            
            # Calculate percentiles
            percentile_map = self._calculate_percentiles(category, all_weighted_scores)
            
            # Update each record
            successful_count = 0
            failed_count = 0
            
            for result in results:
                if result['success']:
                    try:
                        # Extract new scores
                        score_1 = int(result['scores'][0]) if len(result['scores']) > 0 and result['scores'][0].isdigit() else None
                        score_2 = int(result['scores'][1]) if len(result['scores']) > 1 and result['scores'][1].isdigit() else None
                        score_3 = int(result['scores'][2]) if len(result['scores']) > 2 and result['scores'][2].isdigit() else None
                        score_4 = int(result['scores'][3]) if len(result['scores']) > 3 and result['scores'][3].isdigit() else None
                        weighted_score = result['weighted_score']
                        percentile = percentile_map.get(weighted_score, 0)
                        
                        # Update only the scoring columns
                        update_query = f"""
                        UPDATE {category} 
                        SET score_1 = ?, score_2 = ?, score_3 = ?, score_4 = ?, 
                            weighted_score = ?, percentile = ?
                        WHERE id = ?
                        """
                        
                        cursor.execute(update_query, (
                            score_1, score_2, score_3, score_4, 
                            weighted_score, percentile, result['id']
                        ))
                        
                        successful_count += 1
                        
                    except Exception as e:
                        print(f"Error updating record {result['id']}: {e}")
                        failed_count += 1
                else:
                    print(f"Failed to process record {result['id']}: {result.get('error', 'Unknown error')}")
                    failed_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"Ã¢Å“â€œ Successfully updated {successful_count} records in {category}")
            if failed_count > 0:
                print(f"Ã¢Å“â€” Failed to update {failed_count} records in {category}")
            
        except Exception as e:
            print(f"Ã¢Å“â€” Error updating database for {category}: {e}")
    
    def retrain_design_category(self):
        """Retrain the Design category with the new design-specific scoring prompt"""
        category = self.design_category
        
        print(f"\n{'='*60}")
        print(f"RETRAINING CATEGORY: {category}")
        print(f"{'='*60}")
        
        # Get existing projects from database
        projects = self._get_existing_projects(category)
        
        if not projects:
            print(f"No projects found for category {category}")
            return
        
        print(f"Processing {len(projects)} projects for category: {category}")
        
        # Process all projects concurrently
        start_time = time.time()
        results = self._batch_process_projects(projects)
        processing_time = time.time() - start_time
        
        print(f"Processing completed in {processing_time:.2f} seconds")
        
        # Update database with new scores
        self._update_database(category, results)
        
        print(f"Ã¢Å“â€œ Category {category} retraining completed!")
    
    def retrain_all_databases(self):
        """Retrain Design category in both databases"""
        databases = ["projects.db", "workex.db"]
        
        print(f"\n{'='*80}")
        print("STARTING DESIGN CATEGORY RETRAINING")
        print(f"Category to retrain: {self.design_category}")
        print(f"{'='*80}")
        
        overall_start_time = time.time()
        
        for db_name in databases:
            if os.path.exists(db_name):
                print(f"\n{'#'*60}")
                print(f"PROCESSING DATABASE: {db_name}")
                print(f"{'#'*60}")
                
                # Create new retrainer instance for each database
                retrainer = DesignRetrainer(
                    db_path=db_name,
                    max_workers=15,
                    max_concurrent_per_key=5
                )
                
                retrainer.retrain_design_category()
                
                # Add usage stats from this instance
                self.request_count += retrainer.request_count
                for key, count in retrainer.requests_per_key.items():
                    self.requests_per_key[key] += count
            else:
                print(f"Database {db_name} not found, skipping...")
        
        overall_time = time.time() - overall_start_time
        
        print(f"\n{'='*80}")
        print("DESIGN RETRAINING COMPLETED")
        print(f"Total time: {overall_time:.2f} seconds")
        print(f"{'='*80}")
        
        # Print API usage summary
        self.print_api_usage_summary()
    
    def print_api_usage_summary(self):
        """Print summary of API key usage"""
        print("\n" + "="*50)
        print("API USAGE SUMMARY")
        print("="*50)
        print(f"Total requests made: {self.request_count}")
        for i, count in self.requests_per_key.items():
            print(f"API Key #{i + 1}: {count} requests")
        if self.request_count > 0:
            print(f"Average requests per key: {self.request_count / len(self.api_keys):.1f}")
        print("="*50)
