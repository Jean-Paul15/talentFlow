"""Dense Qdrant query helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from .backend_preview import QdrantBackendPreviewMixin


class QdrantBackendDenseMixin:
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = None,
        force_hybrid: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        limit = limit or self.default_limit
        if self.client is None:
            raise RuntimeError("Qdrant backend indisponible (qdrant-client manquant ou config invalide)")
        query_vector = self.embedding_service.embed_single(query)
        if query_vector is None:
            raise RuntimeError("Embedding model indisponible")
        qdrant_filter = self._build_qdrant_filter(filters)
        hybrid_effective = self.hybrid_enabled if force_hybrid is None else bool(force_hybrid)
        if hybrid_effective and str(query or "").strip():
            return self._search_hybrid_rrf(query=query, query_vector=query_vector, qdrant_filter=qdrant_filter, limit=limit)
        hits = self._query_qdrant(query_vector=query_vector, limit=limit, qdrant_filter=qdrant_filter)
        rows = [self._format_qdrant_hit(hit) for hit in hits]
        for row in rows:
            row["_search_mode"] = "semantic_dense"
            row["_hybrid_strategy"] = "dense_only"
            row["_backend"] = self.name
        return rows

    def search_by_vector(
        self,
        *,
        query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = None,
    ) -> List[Dict[str, Any]]:
        limit = limit or self.default_limit
        if self.client is None:
            raise RuntimeError("Qdrant backend indisponible (qdrant-client manquant ou config invalide)")
        qdrant_filter = self._build_qdrant_filter(filters)
        hits = self._query_qdrant(query_vector=query_vector, limit=limit, qdrant_filter=qdrant_filter)
        rows = [self._format_qdrant_hit(hit) for hit in hits]
        for row in rows:
            row["_search_mode"] = "semantic_vector"
            row["_backend"] = self.name
        return rows

    def health(self) -> Dict[str, Any]:
        ok = False
        collection_exists = False
        points_count = 0
        try:
            if self.client is not None:
                info = self.client.get_collection(self.collection_name)
                ok = True
                collection_exists = True
                raw_points_count = getattr(info, "points_count", None)
                try:
                    points_count = int(raw_points_count) if raw_points_count is not None else 0
                except Exception:
                    points_count = 0
        except Exception as err:
            logger.warning(f"Health Qdrant backend: {err}")
        return {
            "backend": self.name,
            "ok": ok and collection_exists,
            "elasticsearch": False,
            "qdrant": ok and collection_exists,
            "index_exists": collection_exists,
            "doc_count": points_count,
            "index_name": self.collection_name,
            "qdrant_url": self.url,
            "hybrid_enabled": self.hybrid_enabled,
        }

    def _query_qdrant(self, *, query_vector: List[float], limit: int, qdrant_filter: Any):
        if hasattr(self.client, "query_points"):
            kwargs = {
                "collection_name": self.collection_name,
                "query": query_vector,
                "limit": limit,
                "with_payload": True,
            }
            if self.sparse_enabled:
                kwargs["using"] = "dense"
            if qdrant_filter is not None:
                kwargs["query_filter"] = qdrant_filter
            result = self.client.query_points(**kwargs)
            points = getattr(result, "points", None)
            return points or []
        kwargs = {
            "collection_name": self.collection_name,
            "query_vector": ("dense", query_vector) if self.sparse_enabled else query_vector,
            "limit": limit,
            "with_payload": True,
        }
        if qdrant_filter is not None:
            kwargs["query_filter"] = qdrant_filter
        return self.client.search(**kwargs)
