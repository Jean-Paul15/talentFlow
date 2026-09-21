# Unified Elasticsearch Factory - UNIQUE ES client pour tout le backend
from elasticsearch import Elasticsearch
from typing import Optional
import logging
from .config import get_es_config

logger = logging.getLogger(__name__)

class ElasticsearchFactory:
    """Elasticsearch singleton"""
    
    _instance: Optional[Elasticsearch] = None
    
    @classmethod
    def get_client(cls) -> Elasticsearch:
        """Get ES client - shared across all services"""
        if cls._instance is None:
            config = get_es_config()
            
            hosts = config.get("hosts", ["localhost:9200"])
            
            cls._instance = Elasticsearch(
                hosts=hosts,
                verify_certs=False,
                ssl_show_warn=False,
                max_retries=2,
                retry_on_timeout=True,
                request_timeout=30
            )
            
            try:
                info = cls._instance.info()
                logger.info(f"ES connected: {info['version']['number']}")
            except Exception as e:
                logger.error(f"ES connection error: {e}")
        
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close ES connection"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            logger.info("Elasticsearch closed")

# Convenience function
def get_es() -> Elasticsearch:
    """Get ES client - use this everywhere"""
    return ElasticsearchFactory.get_client()
