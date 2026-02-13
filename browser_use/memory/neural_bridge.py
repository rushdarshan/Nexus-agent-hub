
import sqlite3
import json
import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
DB_PATH = "nexus_memory.db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

class NeuralBridge:
    """
    Cross-Platform Semantic Memory Bridge.
    Connects Browser, Android, and Desktop agents via a shared vector space.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = Path(db_path)
        self.model = None
        self._init_model()
        
    def _init_model(self):
        """Initialize the embedding model (lazy load)"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(f"🧠 Neural Bridge: Loaded embedding model {EMBEDDING_MODEL_NAME}")
        except ImportError:
            logger.warning("⚠️ Neural Bridge: sentence-transformers not found. Semantic search disabled (using hashlib fallback).")
            self.model = None
            
    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if self.model:
            return self.model.encode(text)
        else:
            # Fallback: Create a deterministic "embedding" from hash (not semantic, but compatible structure)
            # This is a placeholder to prevent crashes, but won't give semantic results
            hash_bytes = hashlib.md5(text.encode()).digest()
            # Create a float array from bytes
            return np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32) / 255.0

    def store_memory(self, content: str, metadata: Dict[str, Any]):
        """Store a semantic memory"""
        embedding = self._get_embedding(content)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Serialize embedding
        if isinstance(embedding, np.ndarray):
            embedding_blob = embedding.tobytes()
        else:
            embedding_blob = None # Should not happen with _get_embedding returning array
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO vectors (content_hash, embedding, metadata, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (
                    content_hash,
                    embedding_blob,
                    json.dumps(metadata),
                ))
                conn.commit()
            logger.debug(f"🧠 Neural Bridge: Stored memory hash={content_hash[:8]}")
        except Exception as e:
            logger.error(f"❌ Neural Bridge Store Error: {e}")

    def query_similar(self, query: str, limit: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Find strictly similar memories (Cosine Similarity)"""
        query_embedding = self._get_embedding(query)
        
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT content_hash, embedding, metadata FROM vectors")
                
                rows = cursor.fetchall()
                for row in rows:
                    content_hash, embedding_blob, metadata_json = row
                    
                    if not embedding_blob:
                        continue
                        
                    stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    
                    # Cosine Similarity
                    if self.model: # If model exists, embeddings are valid vectors
                        # Check dimensions match (handling fallback hash vs partial model output)
                        if stored_embedding.shape != query_embedding.shape:
                            continue
                            
                        # Cosine similarity calculation
                        dot_product = np.dot(query_embedding, stored_embedding)
                        norm_q = np.linalg.norm(query_embedding)
                        norm_s = np.linalg.norm(stored_embedding)
                        
                        if norm_q > 0 and norm_s > 0:
                            score = dot_product / (norm_q * norm_s)
                        else:
                            score = 0.0
                    else:
                        # Fallback mode: Exact match or nothing useful
                        score = 1.0 if content_hash == hashlib.md5(query.encode()).hexdigest() else 0.0
                    
                    if score >= min_score:
                        results.append({
                            "hash": content_hash,
                            "score": float(score),
                            "metadata": json.loads(metadata_json) if metadata_json else {}
                        })
                        
            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Neural Bridge Query Error: {e}")
            return []

# Singleton
neural_bridge = NeuralBridge()
