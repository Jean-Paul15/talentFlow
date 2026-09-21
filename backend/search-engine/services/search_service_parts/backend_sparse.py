"""Sparse and hybrid Qdrant query helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from services.retrieval_fusion import rank_by_lexical, rrf_fuse

from .filters_text import _to_plain_list

class QdrantBackendSparseMixin:
    def _search_hybrid_rrf(
        self,
        *,
        query: str,
        query_vector: List[float],
        qdrant_filter: Any,
        limit: int,
    ) -> List[Dict[str, Any]]:
        dense_fetch_limit = max(limit, self.dense_limit)
        dense_hits = self._query_qdrant(query_vector=query_vector, limit=dense_fetch_limit, qdrant_filter=qdrant_filter)
        dense_rows = [self._format_qdrant_hit(hit) for hit in dense_hits]
        for row in dense_rows:
            row["_search_mode"] = "hybrid_rrf"
            row["_hybrid_strategy"] = "qdrant_dense_plus_lexical_rrf"
        sparse_rows = self._try_sparse_bm25_search(query=query, qdrant_filter=qdrant_filter, limit=max(limit, self.lexical_limit))
        if not sparse_rows:
            lexical_pool_limit = max(dense_fetch_limit, self.lexical_limit)
            if len(dense_rows) < lexical_pool_limit:
                extra_hits = self._query_qdrant(query_vector=query_vector, limit=lexical_pool_limit, qdrant_filter=qdrant_filter)
                dense_rows = [self._format_qdrant_hit(hit) for hit in extra_hits]
            sparse_rows = rank_by_lexical(query, dense_rows)
            for row in sparse_rows:
                row["_hybrid_strategy"] = "qdrant_dense_plus_lexical_rrf_local"
        fused = rrf_fuse([("dense", dense_rows), ("lexical", sparse_rows)], k=self.rrf_k, final_limit=limit)
        for row in fused:
            row["_search_mode"] = "hybrid_rrf"
            row["_hybrid_strategy"] = row.get("_hybrid_strategy") or "qdrant_dense_plus_rrf"
        return fused

    def _try_sparse_bm25_search(self, *, query: str, qdrant_filter: Any, limit: int) -> List[Dict[str, Any]]:
        sparse = self._build_sparse_query_vector(query)
        if sparse is None:
            return []
        try:
            hits = self._query_qdrant_sparse(sparse=sparse, limit=limit, qdrant_filter=qdrant_filter)
            rows = [self._format_qdrant_hit(hit) for hit in hits]
            for row in rows:
                row["_search_mode"] = "hybrid_rrf"
                row["_hybrid_strategy"] = "qdrant_dense_plus_sparse_rrf"
            return rows
        except Exception as err:
            logger.debug(f"Sparse/BM25 Qdrant indisponible, fallback lexical local: {err}")
            return []

    def _build_sparse_query_vector(self, query: str):
        query = str(query or "").strip()
        if not query:
            return None
        encoder = self._get_sparse_encoder()
        if encoder is None:
            return None
        try:
            vectors = list(encoder.embed([query]))
            if not vectors:
                return None
            v = vectors[0]
            indices = _to_plain_list(getattr(v, "indices", None))
            values = _to_plain_list(getattr(v, "values", None))
            if not indices or not values:
                return None
            return {"indices": [int(idx) for idx in indices], "values": [float(val) for val in values]}
        except Exception as err:
            logger.debug(f"Sparse query embedding failed: {err}")
            return None

    def _get_sparse_encoder(self):
        if self._sparse_load_attempted:
            return self._sparse_encoder
        self._sparse_load_attempted = True
        try:
            from fastembed import SparseTextEmbedding  # type: ignore

            self._sparse_encoder = SparseTextEmbedding(model_name=self.sparse_model_name)
        except Exception as err:
            logger.debug(f"SparseTextEmbedding indisponible ({self.sparse_model_name}): {err}")
            self._sparse_encoder = None
        return self._sparse_encoder

    def _query_qdrant_sparse(self, *, sparse: Dict[str, List[float]], limit: int, qdrant_filter: Any):
        try:
            from qdrant_client.http import models as qm  # type: ignore
        except Exception as err:
            raise RuntimeError(f"qdrant models indisponibles pour sparse query: {err}") from err
        sparse_vector = qm.SparseVector(indices=sparse["indices"], values=sparse["values"])
        if hasattr(self.client, "query_points"):
            variants = [
                {
                    "collection_name": self.collection_name,
                    "query": sparse_vector,
                    "using": "sparse",
                    "limit": limit,
                    "with_payload": True,
                    **({"query_filter": qdrant_filter} if qdrant_filter is not None else {}),
                }
            ]
            for kwargs in variants:
                try:
                    result = self.client.query_points(**kwargs)
                    points = getattr(result, "points", None)
                    if points is not None:
                        return points
                except Exception:
                    continue
        if hasattr(self.client, "search"):
            kwargs = {
                "collection_name": self.collection_name,
                "query_vector": ("sparse", sparse_vector),
                "limit": limit,
                "with_payload": True,
            }
            if qdrant_filter is not None:
                kwargs["query_filter"] = qdrant_filter
            return self.client.search(**kwargs)
        raise RuntimeError("Sparse query Qdrant non supportee par cette version client")

    def _build_qdrant_filter(self, filters: Dict[str, Any]):
        if not filters:
            return None
        try:
            from qdrant_client.http import models as qm  # type: ignore
        except Exception:
            return None
        conditions = []
        if filters.get("location"):
            conditions.append(qm.FieldCondition(key="location", match=qm.MatchValue(value=str(filters["location"]))))
        if filters.get("contract_type"):
            conditions.append(qm.FieldCondition(key="contract_type", match=qm.MatchValue(value=str(filters["contract_type"]))))
        if filters.get("skills"):
            for skill in filters["skills"]:
                conditions.append(qm.FieldCondition(key="hard_skills", match=qm.MatchValue(value=str(skill))))
        if filters.get("source_name"):
            conditions.append(qm.FieldCondition(key="source_name", match=qm.MatchValue(value=str(filters["source_name"]))))
        if filters.get("country"):
            conditions.append(qm.FieldCondition(key="country", match=qm.MatchValue(value=str(filters["country"]))))
        if not conditions:
            return None
        return qm.Filter(must=conditions)
