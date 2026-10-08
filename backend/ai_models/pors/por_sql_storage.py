import json
import pandas as pd
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import sys
import os
from pathlib import Path
import ast
import argparse

# Add the parent directory of 'backend' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.database import PORSessionLocal, create_tables, por_engine
from database_models.resume_models import POR, PORBase

def extract_domain_from_filepath(file_path: str) -> str:
    """
    Extracts domain from file path by getting the second parent directory.
    Example: "/workspace/resumes/Consult/synthetic/candidate.pdf"
    Returns: "Consult"
    """
    try:
        path_parts = Path(file_path).parts
        # Find the index of the repository directory and get the next one
        for i, part in enumerate(path_parts):
            if "Resume Repository" in part or "Internship Resume Repository" in part:
                if i + 1 < len(path_parts):
                    return path_parts[i + 1]
        
        # Fallback: if pattern not found, try to get a reasonable directory
        if len(path_parts) >= 3:
            return path_parts[-3]  # Third from last
        
        return "Unknown"
    except Exception as e:
        print(f"Error extracting domain from {file_path}: {e}")
        return "Unknown"

def parse_por_data(por_string: str) -> List[Dict[str, Any]]:
    """
    Parses the POR string data into a list of dictionaries.
    Handles both JSON string format and Python literal format.
    """
    if not por_string or pd.isna(por_string) or por_string.strip() == '':
        return []
    
    try:
        # First try parsing as JSON
        if isinstance(por_string, str):
            por_data = json.loads(por_string)
        else:
            por_data = por_string
            
        # Ensure it's a list
        if not isinstance(por_data, list):
            por_data = [por_data]
            
        return por_data
    except json.JSONDecodeError:
        try:
            # Try parsing as Python literal (in case it's stored as string representation)
            por_data = ast.literal_eval(por_string)
            if not isinstance(por_data, list):
                por_data = [por_data]
            return por_data
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing POR data: {por_string[:100]}... Error: {e}")
            return []

def store_pors_from_csv(csv_file_path: str, db_session: Session):
    """
    Reads CSV file and stores all PORs in the database.
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        print(f"Loaded CSV with {len(df)} rows")
        
        total_pors_stored = 0
        rows_processed = 0
        
        for index, row in df.iterrows():
            try:
                # Extract domain from file path
                file_path = row['file_path']
                domain = extract_domain_from_filepath(file_path)
                
                # Parse POR data
                por_string = row['positions_of_responsibility']
                por_list = parse_por_data(por_string)
                
                if por_list:
                    # Store each POR
                    for por_data in por_list:
                        try:
                            new_por = POR(
                                title=por_data.get("title"),
                                organization=por_data.get("organization"),
                                duration=por_data.get("duration"),
                                responsibilities=por_data.get("responsibilities"),
                                achievements=por_data.get("achievements"),
                                domain=domain
                            )
                            db_session.add(new_por)
                            total_pors_stored += 1
                        except Exception as e:
                            print(f"Error storing POR {por_data}: {e}")
                
                rows_processed += 1
                
                # Commit every 100 rows to avoid large transactions
                if rows_processed % 100 == 0:
                    db_session.commit()
                    print(f"Processed {rows_processed} rows, stored {total_pors_stored} PORs so far...")
                    
            except Exception as e:
                print(f"Error processing row {index}: {e}")
                continue
        
        # Final commit
        db_session.commit()
        print(f"\nCompleted processing!")
        print(f"Total rows processed: {rows_processed}")
        print(f"Total PORs stored: {total_pors_stored}")
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        db_session.rollback()

def verify_stored_data(db_session: Session, limit: int = 5):
    """
    Verifies that data was stored correctly by querying a few records.
    """
    print(f"\nVerifying stored data (showing first {limit} records):")
    results = db_session.query(POR).limit(limit).all()
    
    for i, por in enumerate(results, 1):
        print(f"\nRecord {i}:")
        print(f"  Title: {por.title}")
        print(f"  Organization: {por.organization}")
        print(f"  Duration: {por.duration}")
        print(f"  Domain: {por.domain}")
        print(f"  Responsibilities: {por.responsibilities}")
        print(f"  Achievements: {por.achievements}")

def get_domain_statistics(db_session: Session):
    """
    Shows statistics about domains in the database.
    """
    print("\nDomain Statistics:")
    results = db_session.query(POR.domain, db_session.query(POR).filter_by(domain=POR.domain).count().label('count')).distinct().all()
    
    # Get domain counts
    domain_counts = {}
    for por in db_session.query(POR).all():
        domain = por.domain or "Unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    for domain, count in sorted(domain_counts.items()):
        print(f"  {domain}: {count} PORs")
