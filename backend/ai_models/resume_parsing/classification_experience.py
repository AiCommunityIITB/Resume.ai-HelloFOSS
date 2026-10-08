import pandas as pd
import google.generativeai as genai
import concurrent.futures
import ast
import json
import os
import time
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv


load_dotenv()
# Set your Gemini API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


# List of domains
DOMAINS = [
    "Analytics", "Consult", "Design", "Finance", "IT-Software", "AI Developer", "Quantitative Finance", "Strategy"
]


def print_loading_bar(completed, total, bar_length=50, prefix="Progress"):
    """
    Print a loading bar with real-time updates
    """
    percent = float(completed) / total
    filled_length = int(bar_length * percent)
    
    # Create the bar
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    # Calculate rate and ETA
    current_time = time.time()
    if not hasattr(print_loading_bar, 'start_time'):
        print_loading_bar.start_time = current_time
    
    elapsed = current_time - print_loading_bar.start_time
    rate = completed / elapsed if elapsed > 0 else 0
    eta = (total - completed) / rate if rate > 0 and completed < total else 0
    
    # Format the progress line
    progress_line = f"\r🤖 {prefix}: [{bar}] {completed}/{total} ({percent*100:.1f}%) | "
    progress_line += f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s"
    
    sys.stdout.write(progress_line)
    sys.stdout.flush()
    
    # Print newline when complete
    if completed >= total:
        print()


def create_resume_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Create a mapping from unique file paths to resume numbers (Resume1, Resume2, etc.)
    """
    print("📋 Creating resume number mapping from unique file paths...")
    
    # Get unique file paths (excluding NaN values)
    unique_paths = df['file_path'].dropna().unique()
    
    # Create mapping dictionary
    resume_mapping = {}
    for i, path in enumerate(unique_paths, 1):
        resume_mapping[path] = f"Resume{i}"
    
    print(f" Created mapping for {len(resume_mapping)} unique file paths")
    print(f" Sample mappings:")
    for i, (path, resume_no) in enumerate(list(resume_mapping.items())[:3]):
        print(f"   • {resume_no}: {path[:80]}{'...' if len(path) > 80 else ''}")
    
    return resume_mapping


def classify_company_domain(company_name: str) -> Tuple[str, str]:
    """
    Classify a company from CORE domain into one of the predefined domains using LLM.
    Returns: (classified_domain, reason)
    """
    model = genai.GenerativeModel('gemini-2.5-flash')


    generation_config = genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.8,
        top_k=40,
        response_mime_type="application/json",
    )
    
    # Prompt for company domain classification
    prompt = f"""
    Classify the company "{company_name}" into EXACTLY ONE of these domains: {', '.join(DOMAINS)}.
    
    Domain definitions:
    - Analytics: Data analysis, business intelligence, market research companies
    - Consult: Management consulting, business consulting, advisory services
    - Design: UI/UX design, graphic design, product design, creative agencies
    - Finance: Banking, investment, financial services, fintech
    - IT-Software: Software development, technology services, IT companies
    - AI Developer: AI/ML companies, artificial intelligence startups
    - Quantitative Finance: Hedge funds, algorithmic trading, quantitative analysis
    - Strategy: Strategic consulting, business strategy, corporate strategy


    Choose the best fit based on the company's primary business. If uncertain, choose the closest match.


    Output ONLY in this JSON format (no extra text):
    {{
        "classification": "one of the domains",
        "reason": "brief explanation (1-2 sentences)"
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        result = json.loads(response.text.strip())
        classification = result.get('classification', 'CORE')
        reason = result.get('reason', 'No reason provided')
        
        # Validate that the classification is in the allowed domains
        if classification not in DOMAINS:
            print(f"⚠️  Invalid classification '{classification}' for company '{company_name}', keeping as CORE")
            return 'CORE', f"Invalid classification: {classification}"
        
        return classification, reason
    except Exception as e:
        print(f"❌ Error classifying company '{company_name}': {str(e)}")
        return 'CORE', f"Error classifying: {str(e)}"


def extract_company_name_from_path(file_path: str) -> str:
    """
    Extract company name from file path.
    Expected format: 'Resume.ai/Internship Resume Repository 2025-26/CORE/Microsoft/file.pdf'
    Returns the company name (Microsoft in this case)
    """
    if pd.isna(file_path) or file_path == '':
        return 'Unknown'
    
    try:
        path_parts = file_path.strip('/').split('/')
        
        # Find the index of 'CORE' or 'Core'
        for i, part in enumerate(path_parts):
            if part.upper() == 'CORE':
                # Company name should be the next folder
                if i + 1 < len(path_parts):
                    return path_parts[i + 1]
        
        return 'Unknown'
    except Exception as e:
        print(f"⚠️  Error extracting company name from path '{file_path}': {e}")
        return 'Unknown'


def extract_domain_from_path(file_path):
    """
    Extract domain from file path. Expected format:
    'Resume.ai/Internship Resume Repository 2025-26/IT-Software/Microsoft/2 Page Tech - Astha Agarwal.pdf'
    Returns the second parent folder (IT-Software in this case)
    
    Special handling for CORE domain:
    - Extracts company name and classifies it using LLM
    - Replaces CORE with the classified domain
    """
    if pd.isna(file_path) or file_path == '':
        return 'Unknown'
    
    try:
        # Split the path and get path components
        path_parts = file_path.strip('/').split('/')
        
        # Find the index of 'Internship Resume Repository 2025-26' or similar pattern
        # The domain should be the next folder after this
        for i, part in enumerate(path_parts):
            if 'Resume Repository' in part or 'Internship' in part:
                if i + 1 < len(path_parts):
                    domain = path_parts[i + 1]
                    
                    # Check if domain is CORE (case-insensitive)
                    if domain.upper() == 'CORE':
                        print(f"🔍 Found CORE domain for path: {file_path}")
                        company_name = extract_company_name_from_path(file_path)
                        print(f"🏢 Company name extracted: {company_name}")
                        
                        if company_name != 'Unknown':
                            classified_domain, reason = classify_company_domain(company_name)
                            print(f"🤖 Classified {company_name} as '{classified_domain}' - {reason}")
                            return classified_domain
                        else:
                            print(f"❌ Could not extract company name, keeping as CORE")
                            return 'CORE'
                    
                    return domain
        
        # Fallback: if pattern not found, try to get what looks like a domain
        # Look for known domains in the path
        for part in path_parts:
            if part in DOMAINS:
                return part
            # Check for CORE case-insensitive
            if part.upper() == 'CORE':
                company_name = extract_company_name_from_path(file_path)
                if company_name != 'Unknown':
                    classified_domain, reason = classify_company_domain(company_name)
                    print(f"🤖 Fallback: Classified {company_name} as '{classified_domain}' - {reason}")
                    return classified_domain
                return 'CORE'
        
        # If no known domain found, return the folder that might be a domain
        # Usually it's after Resume.ai/repository_name/
        if len(path_parts) >= 4:
            domain = path_parts[3]
            if domain.upper() == 'CORE':
                company_name = extract_company_name_from_path(file_path)
                if company_name != 'Unknown':
                    classified_domain, reason = classify_company_domain(company_name)
                    print(f"🤖 Final fallback: Classified {company_name} as '{classified_domain}' - {reason}")
                    return classified_domain
                return 'CORE'
            return domain
        
        return 'Unknown'
    except Exception as e:
        print(f"⚠️  Error extracting domain from path '{file_path}': {e}")
        return 'Unknown'


def safe_parse_experiences(experiences_str):
    """
    Safely parse experiences string with multiple fallback methods
    """
    if pd.isna(experiences_str) or experiences_str == '':
        return []
    
    # Method 1: Try ast.literal_eval first
    try:
        experiences_list = ast.literal_eval(experiences_str)
        if isinstance(experiences_list, list):
            return experiences_list
    except (ValueError, SyntaxError) as e:
        pass  # Try next method
    
    # Method 2: Try json.loads
    try:
        experiences_list = json.loads(experiences_str)
        if isinstance(experiences_list, list):
            return experiences_list
    except (ValueError, json.JSONDecodeError) as e:
        pass  # Try next method
    
    # Method 3: Try eval (less safe, but sometimes necessary)
    try:
        experiences_list = eval(experiences_str)
        if isinstance(experiences_list, list):
            return experiences_list
    except Exception as e:
        pass  # Final fallback
    
    # Method 4: If all else fails, return empty list
    return []


def classify_experience(experience: Dict) -> Tuple[str, str, str]:
    """
    Calls Gemini API to classify an experience.
    Returns: (experience_json, classification, reason)
    """
    model = genai.GenerativeModel('gemini-2.5-flash')


    generation_config = genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.8,
        top_k=40,
        response_mime_type="application/json",
    )
    
    # Convert experience dict to a readable string for the prompt
    experience_str = json.dumps(experience, indent=2)
    
    # Prompt for classification
    prompt = f"""
    Classify the following work experience into EXACTLY ONE of these domains: {', '.join(DOMAINS)}.
    Choose the best fit based on the job title, company, responsibilities, achievements, and technologies used.
    If it doesn't fit any, choose the closest.


    Experience details:
    {experience_str}


    Output ONLY in this JSON format (no extra text):
    {{
        "classification": "one of the domains",
        "reason": "brief explanation (1-2 sentences)"
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        # Parse the response (assuming it's valid JSON)
        result = json.loads(response.text.strip())
        classification = result.get('classification', 'Unknown')
        reason = result.get('reason', 'No reason provided')
    except Exception as e:
        classification = 'Unknown'
        reason = f"Error classifying: {str(e)}"
    
    # Return experience as JSON string, classification, reason
    return json.dumps(experience), classification, reason


def process_experiences(df: pd.DataFrame) -> pd.DataFrame:
    print(f"🔄 Starting to process {len(df)} documents...")
    print("=" * 60)
    
    # Create resume number mapping first
    resume_mapping = create_resume_mapping(df)
    print("=" * 60)
    
    # Phase 1: Extract and parse experiences from documents
    print("📋 Phase 1: Extracting experiences from documents...")
    all_experiences = []
    all_domains = []  # Store corresponding domains for each experience
    all_resume_nos = []  # Store corresponding resume numbers for each experience
    failed_rows = 0
    processed_docs = 0
    
    start_time = time.time()
    
    for idx, row in df.iterrows():
        processed_docs += 1
        experiences_list = safe_parse_experiences(row['experience'])
        
        # Extract domain from file path (now handles CORE classification)
        file_path = row.get('file_path', '')
        domain = extract_domain_from_path(file_path)
        
        # Get resume number from mapping
        resume_no = resume_mapping.get(file_path, 'Unknown')
        
        if experiences_list:
            # Add each experience and associate it with the extracted domain and resume number
            all_experiences.extend(experiences_list)
            # Add the same domain and resume number for each experience from this document
            all_domains.extend([domain] * len(experiences_list))
            all_resume_nos.extend([resume_no] * len(experiences_list))
            print(f" Document {processed_docs}/{len(df)}: Found {len(experiences_list)} experiences from {resume_no} - domain '{domain}' (Total: {len(all_experiences)})")
        else:
            failed_rows += 1
            print(f"❌ Document {processed_docs}/{len(df)}: Failed to parse experiences from {resume_no} - '{domain}'")
        
        # Progress update every 10 documents
        if processed_docs % 10 == 0:
            elapsed = time.time() - start_time
            print(f" Progress: {processed_docs}/{len(df)} documents processed in {elapsed:.1f}s")
    
    parsing_time = time.time() - start_time
    print(f"\n✨ Phase 1 Complete!")
    print(f"📈 Successfully parsed {len(all_experiences)} experiences from {len(df)} documents")
    print(f"❌ Failed to parse {failed_rows} documents")
    print(f"⏱️  Parsing took {parsing_time:.1f} seconds")
    
    # Show domain distribution
    if all_domains:
        print(f"\n📂 Domain Distribution from File Paths:")
        domain_counts = pd.Series(all_domains).value_counts()
        for domain, count in domain_counts.items():
            percentage = count / len(all_domains) * 100
            print(f"   • {domain}: {count} experiences ({percentage:.1f}%)")
    
    # Show resume number distribution
    if all_resume_nos:
        print(f"\n📄 Resume Distribution:")
        resume_counts = pd.Series(all_resume_nos).value_counts().sort_index()
        for resume_no, count in resume_counts.head(10).items():  # Show first 10
            percentage = count / len(all_resume_nos) * 100
            print(f"   • {resume_no}: {count} experiences ({percentage:.1f}%)")
        if len(resume_counts) > 10:
            print(f"   • ... and {len(resume_counts) - 10} more resumes")
    
    print("=" * 60)
    
    # Phase 2: Classify experiences using Gemini API with Loading Bar
    print(f"🤖 Phase 2: Classifying {len(all_experiences)} experiences using Gemini API...")
    print("🔄 Initializing classification with loading bar...")
    
    results = []
    completed_count = 0
    
    # Reset the loading bar timer
    if hasattr(print_loading_bar, 'start_time'):
        delattr(print_loading_bar, 'start_time')
    
    # Initial loading bar display
    print_loading_bar(0, len(all_experiences), prefix="Classifying")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_data = {executor.submit(classify_experience, exp): (exp, domain, resume_no) 
                         for exp, domain, resume_no in zip(all_experiences, all_domains, all_resume_nos)}
        
        for future in concurrent.futures.as_completed(future_to_data):
            try:
                experience_json, classification, reason = future.result()
                experience, domain, resume_no = future_to_data[future]
                
                results.append({
                    'experience': experience_json,
                    'classification': classification,
                    'reason': reason,
                    'domain': domain,  # Add the extracted domain (now handles CORE->classified domain)
                    'resume_no': resume_no  # Add the resume number
                })
                
                completed_count += 1
                
                # Update loading bar for every completed experience
                print_loading_bar(completed_count, len(all_experiences), prefix="Classifying")
                    
            except Exception as e:
                # Still need to add the domain and resume number even for failed classifications
                experience, domain, resume_no = future_to_data[future]
                results.append({
                    'experience': json.dumps(experience),
                    'classification': 'Unknown',
                    'reason': f"Error classifying: {str(e)}",
                    'domain': domain,
                    'resume_no': resume_no
                })
                completed_count += 1
                print_loading_bar(completed_count, len(all_experiences), prefix="Classifying")
                print(f"\n❌ Error in concurrent call: {e}")
    
    # Ensure loading bar shows 100% completion
    print_loading_bar(len(all_experiences), len(all_experiences), prefix="Classifying")
    
    total_time = time.time() - start_time
    classification_time = time.time() - start_time + parsing_time
    
    print(f"\n🎉 Phase 2 Complete!")
    print(f" Successfully classified {len(results)} experiences")
    print(f" Average rate: {len(results)/(classification_time-parsing_time):.1f} experiences/second")
    print("=" * 60)
    
    # Create new DataFrame with domain and resume_no columns
    classified_df = pd.DataFrame(results)
    
    # Rename 'domain' to 'Domain' for consistency
    if 'domain' in classified_df.columns:
        classified_df = classified_df.rename(columns={'domain': 'Domain'})
    
    return classified_df


# Main execution
