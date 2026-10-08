from pathlib import Path
import json
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(str(Path(__file__).resolve().parents[2]))
from database_models.resume_models import POR
from utils.database import por_engine, PORBase, PORSessionLocal

# Global model instance
_model = None

def get_model():
    """Load the sentence transformer model."""
    global _model
    if _model is None:
        print("Loading SentenceTransformer model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def encode_embedding(embedding: np.ndarray) -> bytes:
    """Convert numpy array to bytes for database storage."""
    return embedding.astype(np.float32).tobytes()

def decode_embedding(blob: bytes, dim: int = 384) -> np.ndarray:
    """Convert bytes back to numpy array."""
    return np.frombuffer(blob, dtype=np.float32).reshape(dim)

def create_comprehensive_text(por_dict: Dict) -> str:
    """Create comprehensive text representation for embedding."""
    responsibilities_text = '; '.join(por_dict.get('responsibilities', [])) if por_dict.get('responsibilities') else ""
    achievements_text = '; '.join(por_dict.get('achievements', [])) if por_dict.get('achievements') else ""
    
    parts = []
    parts.append(f"Position: {por_dict.get('title', '')}")
    parts.append(f"Organization: {por_dict.get('organization', '')}")
    
    if por_dict.get('duration'):
        parts.append(f"Duration: {por_dict.get('duration')}")
    
    if responsibilities_text:
        parts.append(f"Key Responsibilities: {responsibilities_text}")
        parts.append(f"Duties: {responsibilities_text}")
    
    if achievements_text:
        parts.append(f"Major Achievements: {achievements_text}")
        parts.append(f"Accomplishments: {achievements_text}")
    
    if por_dict.get('title'):
        parts.append(f"Role: {por_dict.get('title')}")
    
    if por_dict.get('organization'):
        parts.append(f"Company: {por_dict.get('organization')}")
        parts.append(f"Institution: {por_dict.get('organization')}")
    
    return ". ".join(filter(None, parts)) + "."

def parse_json_field(field_value):
    """Parse JSON field that might be stored as string."""
    if not field_value:
        return []
    
    if isinstance(field_value, list):
        return field_value
    
    if isinstance(field_value, str):
        try:
            parsed = json.loads(field_value)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return [field_value] if field_value.strip() else []
    
    return []

def generate_and_store_embeddings(session: Session, batch_size: int = 100, force_regenerate: bool = False):
    """Generate embeddings for all PORs and store them in the database."""
    print("Starting embedding generation and storage process...")
    
    model = get_model()
    
    # Query PORs that need embeddings - ADD ORDER BY FOR MSSQL COMPATIBILITY
    if force_regenerate:
        query = session.query(POR).filter(
            POR.title != None, 
            POR.organization != None
        ).order_by(POR.id)  # FIX: Added order_by for MSSQL
        print("Force regenerating all embeddings...")
    else:
        query = session.query(POR).filter(
            POR.title != None, 
            POR.organization != None, 
            POR.embedding == None
        ).order_by(POR.id)  # FIX: Added order_by for MSSQL
        print("Generating embeddings for PORs without existing embeddings...")
    
    total_count = query.count()
    print(f"Found {total_count} POR records to process.")
    
    if total_count == 0:
        print("No PORs need embedding generation. Use force_regenerate=True to regenerate all.")
        return
    
    processed_count = 0
    offset = 0
    
    while offset < total_count:
        # Get batch of PORs
        pors = query.offset(offset).limit(batch_size).all()
        if not pors:
            break
        
        print(f"Processing batch {offset//batch_size + 1}: records {offset + 1} to {offset + len(pors)}")
        
        # Prepare texts for embedding
        texts = []
        valid_pors = []
        
        for por in pors:
            try:
                # Parse responsibilities and achievements
                responsibilities = parse_json_field(por.responsibilities)
                achievements = parse_json_field(por.achievements)
                
                por_dict = {
                    'title': por.title or '',
                    'organization': por.organization or '',
                    'duration': por.duration or '',
                    'responsibilities': responsibilities,
                    'achievements': achievements
                }
                
                text = create_comprehensive_text(por_dict)
                texts.append(text)
                valid_pors.append(por)
                
            except Exception as e:
                print(f"Error processing POR ID {por.id}: {e}")
                continue
        
        if not texts:
            offset += len(pors)
            continue
        
        # Generate embeddings
        try:
            print(f"Generating embeddings for {len(texts)} texts...")
            embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
            
            # Store embeddings
            for idx, por in enumerate(valid_pors):
                embedding_bytes = encode_embedding(embeddings[idx])
                por.embedding = embedding_bytes
                session.add(por)
            
            # Commit batch
            session.commit()
            processed_count += len(valid_pors)
            print(f"Successfully processed {processed_count}/{total_count} PORs")
            
        except Exception as e:
            print(f"Error generating embeddings for batch: {e}")
            session.rollback()
        
        offset += len(pors)
    
    print(f"Embedding generation completed. Processed {processed_count} PORs total.")

def verify_embeddings(session: Session, sample_size: int = 5):
    """Verify that embeddings were stored correctly."""
    print(f"\nVerifying stored embeddings (sampling {sample_size} records)...")
    
    # FIX: Added order_by for MSSQL compatibility
    pors_with_embeddings = session.query(POR).filter(
        POR.embedding != None
    ).order_by(POR.id).limit(sample_size).all()
    
    for i, por in enumerate(pors_with_embeddings, 1):
        try:
            embedding = decode_embedding(por.embedding)
            print(f"Record {i}: POR ID {por.id}, Title: '{por.title}', Embedding shape: {embedding.shape}")
            print(f"  First 5 values: {embedding[:5]}")
            print(f"  Embedding norm: {np.linalg.norm(embedding):.4f}")
        except Exception as e:
            print(f"Error decoding embedding for POR ID {por.id}: {e}")

def get_embedding_statistics(session: Session):
    """Show statistics about stored embeddings."""
    total_pors = session.query(POR).count()
    pors_with_embeddings = session.query(POR).filter(POR.embedding != None).count()
    
    print(f"\nEmbedding Statistics:")
    print(f"Total PORs: {total_pors}")
    print(f"PORs with embeddings: {pors_with_embeddings}")
    print(f"PORs without embeddings: {total_pors - pors_with_embeddings}")
    print(f"Coverage: {(pors_with_embeddings/total_pors*100):.1f}%" if total_pors > 0 else "Coverage: 0%")
