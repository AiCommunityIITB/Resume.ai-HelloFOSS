import json
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from database_models.resume_models import POR

# Global model instance
_model = None

def get_model():
    """Load the sentence transformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

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

def normalize_por_structure(por: Dict) -> Dict:
    """Normalize POR structure to ensure consistency."""
    return {
        "title": por.get('title', ''),
        "organization": por.get('organization', ''),
        "duration": por.get('duration', ''),
        "responsibilities": por.get('responsibilities', []) if isinstance(por.get('responsibilities', []), list) else [],
        "achievements": por.get('achievements', []) if isinstance(por.get('achievements', []), list) else []
    }

def find_most_similar_pors_optimized(session: Session, target_por: Dict, k: int = 5) -> Dict:
    """
    Find most similar PORs using precomputed embeddings.
    
    Args:
        session: SQLAlchemy session
        target_por: Complete target POR dictionary with all fields
        k: Number of similar PORs to return
    
    Returns:
        Dictionary with target POR and top similar PORs
    """
    
    # Normalize target POR structure
    normalized_target = normalize_por_structure(target_por)
    
    # Generate embedding for target POR
    model = get_model()
    target_text = create_comprehensive_text(normalized_target)
    target_embedding = model.encode([target_text], normalize_embeddings=True)[0]
    
    # Load all PORs with precomputed embeddings
    pors_with_embeddings = session.query(POR).filter(POR.embedding != None).all()
    
    if not pors_with_embeddings:
        raise ValueError("No precomputed embeddings found in database. Please run embedding generation first.")
    
    print(f"Loaded {len(pors_with_embeddings)} PORs with embeddings from database")
    
    # Decode embeddings and prepare POR data
    por_embeddings = []
    por_data = []
    
    for por in pors_with_embeddings:
        try:
            # Decode embedding
            embedding = decode_embedding(por.embedding)
            por_embeddings.append(embedding)
            
            # Parse POR data
            responsibilities = parse_json_field(por.responsibilities)
            achievements = parse_json_field(por.achievements)
            
            por_dict = {
                "id": por.id,
                "title": por.title or "",
                "organization": por.organization or "",
                "duration": por.duration or "",
                "responsibilities": responsibilities,
                "achievements": achievements,
                "domain": getattr(por, 'domain', None)
            }
            por_data.append(por_dict)
            
        except Exception as e:
            print(f"Error processing POR ID {por.id}: {e}")
            continue
    
    if not por_embeddings:
        raise ValueError("No valid embeddings could be decoded from database")
    
    # Convert to numpy array for efficient computation
    por_embeddings_np = np.vstack(por_embeddings)
    
    # Compute similarities using precomputed embeddings
    similarities = cosine_similarity([target_embedding], por_embeddings_np)[0]
    
    # Get top k similar PORs
    top_k_indices = np.argsort(similarities)[-k*2:][::-1]  # Get more to filter exact matches
    
    similar_pors = []
    for idx in top_k_indices:
        if similarities[idx] > 0.1:  # Minimum similarity threshold
            por = por_data[idx].copy()
            similarity_score = round(float(similarities[idx]), 4)
            
            # Skip exact matches (same title and organization)
            if (por['title'].lower() == normalized_target['title'].lower() and 
                por['organization'].lower() == normalized_target['organization'].lower() and 
                similarity_score > 0.95):
                continue
            
            por["similarity_score"] = similarity_score
            similar_pors.append(por)
            
            if len(similar_pors) >= k:
                break
    
    return {
        "target_por": normalized_target,
        "top_k_similar": similar_pors,
        "total_pors_analyzed": len(por_data)
    }

def run_por_similarity_optimized(session: Session, target_por: Dict, k: int = 5) -> Dict:
    """
    Main function to run optimized POR similarity analysis using precomputed embeddings.
    
    Args:
        session: SQLAlchemy session
        target_por: Complete target POR dictionary
        k: Number of similar PORs to return
    
    Returns:
        Dictionary with similarity analysis results
    """
    try:
        result = find_most_similar_pors_optimized(session=session, target_por=target_por, k=k)
        return result
    except Exception as e:
        raise ValueError(f"Optimized POR similarity analysis failed: {str(e)}")

def analyze_por_similarity(target_por: Dict, k: int = 5) -> Dict:
    """
    Convenience function with database session management.
    This replaces the original function and uses precomputed embeddings.
    """
    from utils.database import PORSessionLocal
    
    db = PORSessionLocal()
    try:
        return run_por_similarity_optimized(db, target_por, k)
    finally:
        db.close()

# Backward compatibility - keep the original function name but use optimized version
def analyze_por_similarity_updated(target_por: Dict, k: int = 5) -> Dict:
    """Alias for the updated function to maintain backward compatibility."""
    return analyze_por_similarity(target_por, k)

# Example usage and testing
