# Etape 4: Dependency Injection - version simplifiee et Gemini-only
from typing import Optional
import os
import redis
import logging
from elasticsearch import Elasticsearch
from langchain.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class DIContainer:
    """Dependency Injection - composants communs sans runtime LLM local"""

    _instance: Optional["DIContainer"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self.llm = None

            self.embeddings = HuggingFaceEmbeddings(
                model_name=os.getenv(
                    "EMBEDDING_MODEL",
                    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                ),
                cache_folder="/tmp/embeddings",
            )

            self.redis = redis.ConnectionPool(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                max_connections=20,
                socket_keepalive=True,
            )

            es_host = (
                os.getenv("ELASTICSEARCH_HOST")
                or os.getenv("ES_HOST")
                or "localhost"
            )
            es_port = int(
                os.getenv("ELASTICSEARCH_PORT")
                or os.getenv("ES_PORT")
                or "9200"
            )
            self.es = Elasticsearch(
                hosts=[f"{es_host}:{es_port}"],
                max_retries=2,
                retry_on_timeout=True,
            )

            self._initialized = True
            logger.info("DI Container initialized (Gemini-only policy)")
        except Exception as e:
            logger.error(f"DI init error: {e}")
            raise
