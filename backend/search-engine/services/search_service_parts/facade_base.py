"""Facade base mixin."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.embedding_service import EmbeddingService
from services.reranker_service import RerankerService

from .backend_impl import QdrantSearchBackend


class HybridSearchServiceBaseMixin:
    def __init__(self):
        self.backend_name = "qdrant"
        self.embedding_service = EmbeddingService()
        self.backend = QdrantSearchBackend(embedding_service=self.embedding_service)
        self.reranker = RerankerService()

    def _backend_search(
        self,
        *,
        query: str,
        filters: Optional[Dict[str, Any]],
        limit: int,
        force_hybrid: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        if force_hybrid is None:
            return self.backend.search(query=query, filters=filters, limit=limit)
        try:
            return self.backend.search(query=query, filters=filters, limit=limit, force_hybrid=force_hybrid)
        except TypeError:
            return self.backend.search(query=query, filters=filters, limit=limit)
