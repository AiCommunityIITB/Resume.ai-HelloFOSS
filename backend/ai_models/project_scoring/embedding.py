from pathlib import Path
"""
Script to generate and save embeddings for all project tables in the database.
Uses 'all-MiniLM-L6-v2' model to create embeddings from concatenation of 'title' and 'description' fields.
"""
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
"""
Script to generate and save embeddings for all project tables in the database.
Uses 'all-MiniLM-L6-v2' model to create embeddings from concatenation of 'title' and 'description' fields.
"""

import os
import pickle
import logging
from typing import List, Dict, Any
from sqlalchemy import inspect, text
from sentence_transformers import SentenceTransformer
from utils.database import workex_engine, WorkexSessionLocal, WorkexBase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_embedding_model():
    """Load the sentence transformer model for generating embeddings."""
    logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Model loaded successfully.")
    return model

def get_all_project_tables():
    """Get all table names from the projects database."""
    inspector = inspect(workex_engine)
    table_names = inspector.get_table_names()
    logger.info(f"Found {len(table_names)} tables in workex database: {table_names}")
    return table_names

def serialize_embedding(embedding):
    """Serialize numpy array to bytes for database storage."""
    return pickle.dumps(embedding)

def create_embedding_text(title, description):
    """Create text for embedding by concatenating title and description."""
    title = title or ""
    description = description or ""
    return f"{title} {description}".strip()

def update_table_embeddings(table_name: str, model: SentenceTransformer, session):
    """Update embeddings for all records in a specific table."""
    logger.info(f"Processing table: {table_name}")
    
    try:
        # Check if table has required columns
        inspector = inspect(workex_engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        if 'title' not in columns or 'description' not in columns:
            logger.warning(f"Table {table_name} doesn't have required columns. Skipping.")
            return 0
            
        if 'embedding' not in columns:
            logger.warning(f"Table {table_name} doesn't have embedding column. Skipping.")
            return 0
        
        # Get records needing embeddings
        query = text(f"SELECT id, title, description FROM {table_name} WHERE embedding IS NULL")
        
        try:
            result = session.execute(query)
            records = result.fetchall()
        except Exception as e:
            logger.error(f"Query failed for table {table_name}: {str(e)}")
            return 0
        
        if not records:
            logger.info(f"No records need embedding updates in table {table_name}")
            return 0
        
        logger.info(f"Found {len(records)} records to update in {table_name}")
        
        updated_count = 0
        batch_size = 50
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            texts = []
            record_ids = []
            
            # Process each record in batch
            for record in batch:
                try:
                    record_id = record[0]
                    title = record[1] if len(record) > 1 else ""
                    description = record[2] if len(record) > 2 else ""
                    
                    embedding_text = create_embedding_text(title, description)
                    texts.append(embedding_text)
                    record_ids.append(record_id)
                    
                except Exception as e:
                    logger.warning(f"Skipping problematic record: {str(e)}")
                    continue
            
            # Generate embeddings if we have valid texts
            if not texts:
                logger.warning(f"No valid texts in batch for {table_name}")
                continue
                
            try:
                logger.info(f"Generating {len(texts)} embeddings for {table_name}")
                embeddings = model.encode(texts)
                
                # Update database with embeddings
                for record_id, embedding in zip(record_ids, embeddings):
                    serialized_embedding = serialize_embedding(embedding)
                    
                    update_query = text(f"UPDATE {table_name} SET embedding = :embedding WHERE id = :record_id")
                    session.execute(update_query, {
                        'embedding': serialized_embedding,
                        'record_id': record_id
                    })
                    updated_count += 1
                
                session.commit()
                logger.info(f"Successfully updated {len(embeddings)} records in {table_name}")
                
            except Exception as e:
                logger.error(f"Failed to generate/save embeddings for {table_name}: {str(e)}")
                session.rollback()
                continue
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error processing table {table_name}: {str(e)}")
        return 0

def generate_all_embeddings():
    """Main function to generate embeddings for all project tables."""
    logger.info("Starting embedding generation process...")
    
    # Load model
    model = load_embedding_model()
    
    # Get tables
    table_names = get_all_project_tables()
    
    if not table_names:
        logger.warning("No tables found in workex database")
        return
    
    total_updated = 0
    
    # Process each table
    try:
        with WorkexSessionLocal() as session:
            for table_name in table_names:
                updated_count = update_table_embeddings(table_name, model, session)
                total_updated += updated_count
        
        logger.info(f"Embedding generation completed. Total records updated: {total_updated}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
