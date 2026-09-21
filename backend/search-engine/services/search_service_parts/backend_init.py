"""Backend initialization mixin."""

from __future__ import annotations

import os

from loguru import logger

from services.embedding_service import EmbeddingService

from .filters_base import _env


class QdrantBackendInitMixin:
    def __init__(self, embedding_service: EmbeddingService):
        self.name = "qdrant"
        self.embedding_service = embedding_service
        self.client = None
        self.collection_name = _env("QDRANT_COLLECTION", "talentflow_jobs")
        self.default_limit = int(_env("SEARCH_DEFAULT_LIMIT", "20"))
        self.hybrid_enabled = _env("QDRANT_HYBRID_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
        self.sparse_enabled = _env("QDRANT_ENABLE_SPARSE", "false").lower() in {"1", "true", "yes", "on"}
        self.rrf_k = int(_env("QDRANT_RRF_K", "60"))
        self.dense_limit = int(_env("QDRANT_DENSE_LIMIT", "50"))
        self.lexical_limit = int(_env("QDRANT_LEXICAL_LIMIT", "50"))
        self.url = _env("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.sparse_model_name = _env("QDRANT_SPARSE_MODEL", "Qdrant/bm25")
        self._sparse_encoder = None
        self._sparse_load_attempted = False
        try:
            from qdrant_client import QdrantClient  # type: ignore

            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        except Exception as err:
            logger.warning(f"Qdrant client indisponible: {err}")
            self.client = None
