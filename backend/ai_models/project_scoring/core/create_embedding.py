from sentence_transformers import SentenceTransformer
import sqlite3
import os
import numpy as np
from sqlalchemy import create_engine, MetaData, Column, Integer, String, Float, Text, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import time

# Initialize the sentence transformer model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("Loaded sentence transformer model: all-MiniLM-L6-v2")

def add_embedding_column_to_db(db_path: str):
    """Add embedding column to all tables in a database"""
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping...")
        return
    
    print(f"\nProcessing database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table_name in tables:
        try:
            # Check if embedding column already exists
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'embedding' not in columns:
                # Add embedding column after description
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN embedding BLOB")
                print(f"  Added embedding column to table: {table_name}")
            else:
                print(f"  Embedding column already exists in table: {table_name}")
                
        except sqlite3.Error as e:
            print(f"  Error processing table {table_name}: {e}")
    
    conn.commit()
    conn.close()

def create_embeddings_for_db(db_path: str):
    """Create embeddings for all projects in a database"""
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping...")
        return
    
    print(f"\nCreating embeddings for database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    total_processed = 0
    
    for table_name in tables:
        try:
            print(f"\n  Processing table: {table_name}")
            
            # Check if table has the required columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'description' not in columns or 'embedding' not in columns:
                print(f"    Skipping table {table_name}: missing required columns")
                continue
            
            # Get all rows that don't have embeddings yet
            cursor.execute(f"SELECT id, title, description FROM {table_name} WHERE embedding IS NULL")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"    All rows in {table_name} already have embeddings")
                continue
            
            print(f"    Found {len(rows)} rows without embeddings")
            
            # Process in batches to manage memory
            batch_size = 100
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                batch_texts = []
                batch_ids = []
                
                # Prepare text for embedding (title + description)
                for row_id, title, description in batch:
                    title = title if title else ""
                    description = description if description else ""
                    combined_text = f"{title}\n{description}".strip()
                    
                    batch_texts.append(combined_text)
                    batch_ids.append(row_id)
                
                # Create embeddings for the batch
                print(f"    Processing batch {i//batch_size + 1}/{(len(rows) + batch_size - 1)//batch_size}")
                embeddings = model.encode(batch_texts, show_progress_bar=False)
                
                # Update database with embeddings
                for row_id, embedding in zip(batch_ids, embeddings):
                    # Convert embedding to numpy bytes
                    embedding_bytes = embedding.astype(np.float32).tobytes()
                    
                    cursor.execute(f"UPDATE {table_name} SET embedding = ? WHERE id = ?", 
                                 (embedding_bytes, row_id))
                
                conn.commit()
                total_processed += len(batch)
                print(f"    Processed {len(batch)} embeddings")
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
            
            print(f"    Completed table {table_name}: {len(rows)} embeddings created")
                
        except Exception as e:
            print(f"    Error processing table {table_name}: {e}")
            conn.rollback()
    
    conn.close()
    print(f"\nTotal embeddings created: {total_processed}")

def verify_embeddings(db_path: str):
    """Verify that embeddings were created correctly"""
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping verification...")
        return
    
    print(f"\nVerifying embeddings in database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table_name in tables:
        try:
            # Check if table has embedding column
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'embedding' not in columns:
                print(f"  Table {table_name}: No embedding column")
                continue
            
            # Count total rows and rows with embeddings
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
            rows_with_embeddings = cursor.fetchone()[0]
            
            # Test loading one embedding to verify format
            cursor.execute(f"SELECT embedding FROM {table_name} WHERE embedding IS NOT NULL LIMIT 1")
            sample_embedding = cursor.fetchone()
            
            if sample_embedding:
                embedding_array = np.frombuffer(sample_embedding[0], dtype=np.float32)
                embedding_shape = embedding_array.shape
                print(f"  Table {table_name}: {rows_with_embeddings}/{total_rows} rows have embeddings (shape: {embedding_shape})")
            else:
                print(f"  Table {table_name}: {rows_with_embeddings}/{total_rows} rows have embeddings")
                
        except Exception as e:
            print(f"  Error verifying table {table_name}: {e}")
    
    conn.close()

def main():
    """Main function to process both databases"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Database paths
    projects_db = os.path.join(script_dir, "projects.db")
    workex_db = os.path.join(script_dir, "workex.db")
    
    print("="*60)
    print("EMBEDDING CREATION PROCESS")
    print("="*60)
    
    # Step 1: Add embedding columns to both databases
    print("\nStep 1: Adding embedding columns to databases...")
    add_embedding_column_to_db(projects_db)
    add_embedding_column_to_db(workex_db)
    
    # Step 2: Create embeddings for both databases
    print("\nStep 2: Creating embeddings...")
    start_time = time.time()
    
    create_embeddings_for_db(projects_db)
    create_embeddings_for_db(workex_db)
    
    total_time = time.time() - start_time
    print(f"\nEmbedding creation completed in {total_time:.2f} seconds")
    
    # Step 3: Verify embeddings
    print("\nStep 3: Verifying embeddings...")
    verify_embeddings(projects_db)
    verify_embeddings(workex_db)
    
    print("\n" + "="*60)
    print("PROCESS COMPLETED SUCCESSFULLY")
    print("="*60)
