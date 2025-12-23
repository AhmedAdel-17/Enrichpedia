# Embedding Service for Semantic Understanding
import numpy as np
from typing import List, Optional
import logging


class EmbeddingService:
    """
    Embedding service using sentence-transformers for multilingual text embeddings.
    Uses paraphrase-multilingual-MiniLM-L12-v2 for Arabic and English support.
    """
    
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    def __init__(self):
        self.logger = logging.getLogger("embedding_service")
        self._model = None
        self._model_loaded = False
    
    def _load_model(self) -> None:
        """Lazy load the sentence transformer model."""
        if self._model_loaded:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.logger.info(f"Loading embedding model: {self.MODEL_NAME}")
            self._model = SentenceTransformer(self.MODEL_NAME)
            self._model_loaded = True
            self.logger.info("Embedding model loaded successfully")
        except ImportError:
            self.logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        self._load_model()
        
        if not texts:
            return np.array([])
        
        # Truncate very long texts to avoid memory issues
        truncated_texts = [text[:2000] for text in texts]
        
        embeddings = self._model.encode(
            truncated_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        
        return embeddings
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (embedding_dim,)
        """
        embeddings = self.get_embeddings([text])
        return embeddings[0] if len(embeddings) > 0 else np.array([])
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0
        
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
    
    def compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Compute pairwise cosine similarity matrix.
        
        Args:
            embeddings: numpy array of shape (n_samples, embedding_dim)
            
        Returns:
            numpy array of shape (n_samples, n_samples) with similarity scores
        """
        if len(embeddings) == 0:
            return np.array([[]])
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        normalized = embeddings / norms
        
        # Compute similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)
        
        return similarity_matrix
