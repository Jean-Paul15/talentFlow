# Unified Embeddings Service - UNIQUE cached embeddings pour tout le backend
from langchain.embeddings import HuggingFaceEmbeddings
from typing import List, Optional
import logging
from .config import get_llm_config

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Embeddings singleton - reuse model + cache"""
    
    _instance: Optional[HuggingFaceEmbeddings] = None
    _cache: dict = {}
    
    @classmethod
    def get_embeddings(cls) -> HuggingFaceEmbeddings:
        """Get embeddings model - loaded once in memory"""
        if cls._instance is None:
            config = get_llm_config()
            model_name = config.get("embeddings_model", 
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            
            cls._instance = HuggingFaceEmbeddings(
                model_name=model_name,
                cache_folder="/tmp/embeddings",
                model_kwargs={"device": "cpu"}  # GPU optionnel
            )
            
            # Get dimensions
            test_embed = cls._instance.embed_query("test")
            logger.info(f"Embeddings loaded: {len(test_embed)} dimensions")
        
        return cls._instance
    
    @classmethod
    def embed_query(cls, text: str) -> List[float]:
        """Embed query with caching"""
        cache_key = hash(text)
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        embeddings = cls.get_embeddings()
        result = embeddings.embed_query(text)
        
        # Cache (limite a 1000 embeddings)
        if len(cls._cache) < 1000:
            cls._cache[cache_key] = result
        
        return result
    
    @classmethod
    def embed_documents(cls, texts: List[str]) -> List[List[float]]:
        """Embed documents"""
        embeddings = cls.get_embeddings()
        return embeddings.embed_documents(texts)
    
    @classmethod
    def clear_cache(cls):
        """Clear cache si memoire pleine"""
        cls._cache.clear()

# Convenience function
def get_embeddings_service() -> EmbeddingsService:
    """Get embeddings service"""
    return EmbeddingsService()
