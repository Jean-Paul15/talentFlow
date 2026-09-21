# __init__.py - Expose shared kernel
from .config import ConfigLoader, get_es_config, get_llm_config
from .redis_factory import RedisFactory, get_redis
from .embeddings_service import EmbeddingsService, get_embeddings_service
from .schemas import JobSchema, CVSchema, EmbeddingSchema
from .health import HealthResponse, create_health_response

try:
    from .es_factory import ElasticsearchFactory, get_es
except Exception:  # pragma: no cover
    ElasticsearchFactory = None  # type: ignore
    get_es = None  # type: ignore

__all__ = [
    # Config
    "ConfigLoader",
    "get_es_config",
    "get_llm_config",
    # Redis
    "RedisFactory",
    "get_redis",
    # Elasticsearch
    "ElasticsearchFactory",
    "get_es",
    # Embeddings
    "EmbeddingsService",
    "get_embeddings_service",
    # Schemas
    "JobSchema",
    "CVSchema",
    "EmbeddingSchema",
    # Health
    "HealthResponse",
    "create_health_response",
]
