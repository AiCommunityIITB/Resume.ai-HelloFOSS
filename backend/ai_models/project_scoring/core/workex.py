import sys
import os
import pandas as pd
import time

# Add the backend directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from projectAnalyzer import ProjectAnalyzer
from utils.database import workex_engine, WorkexBase

analyzer = ProjectAnalyzer(engine=workex_engine, base=WorkexBase, db_type="workex")

csv_file = "classified_experience_all.csv"
df = pd.read_csv(csv_file)
make_csv = False
display_output = False  # Set to False for faster processing
out_dir = ""
unique_categories = df['classification'].unique()

print(f"Available categories: {unique_categories}")
print(f"Using {analyzer.max_workers} concurrent workers with {len(analyzer.api_keys)} API keys")

start_time = time.time()

# Process all categories with concurrent processing
for cat in unique_categories:
    print(f"\n{'='*60}")
    print(f"Processing category: {cat}")
    print(f"{'='*60}")
    
    category_start = time.time()
    try:
        analyzer.make_db_concurrent(csv_file, cat, out_dir, make_csv, display_output)
        category_time = time.time() - category_start
        print(f"✓ Completed {cat} in {category_time:.2f} seconds")
    except Exception as e:
        print(f"✗ Error processing {cat}: {str(e)}")

