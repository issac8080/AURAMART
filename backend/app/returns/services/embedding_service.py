"""
Embedding service for semantic similarity. Uses the shared SentenceTransformer
from recommend.rag_products so weights are loaded only once in the process.
"""
import numpy as np
from typing import List


def _get_shared_model():
    """Lazy import to avoid loading returns module at startup when returns router is disabled."""
    try:
        from recommend.rag_products import _get_embedding_model
        return _get_embedding_model()
    except Exception:
        return None


class EmbeddingService:
    """Service for generating embeddings using the shared RAG embedding model (no duplicate load)."""

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        model = _get_shared_model()
        if model is None:
            return np.zeros(384, dtype=np.float32)  # all-MiniLM-L6-v2 dimension
        return model.encode(text, convert_to_numpy=True)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        model = _get_shared_model()
        if model is None:
            return np.zeros((len(texts), 384), dtype=np.float32)
        return model.encode(texts, convert_to_numpy=True)

    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))


# Global instance (no model loaded here; uses shared model on first embed call)
embedding_service = EmbeddingService()
