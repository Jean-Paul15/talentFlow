"""Search operations for the hybrid search facade."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .filters_impl import _dedupe_and_filter_results
from .ranking import _apply_user_facing_quality_policies


class HybridSearchServiceSearchMixin:
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = None,
        rerank: Optional[bool] = None,
        rerank_top_k: Optional[int] = None,
        candidate_pool_size: Optional[int] = None,
        force_hybrid: Optional[bool] = None,
        return_meta: bool = False,
    ) -> Any:
        requested_limit = limit or getattr(self.backend, "default_limit", 20)
        do_rerank = self.reranker.should_rerank(rerank)
        pool_limit = candidate_pool_size or requested_limit
        if do_rerank:
            pool_limit = max(pool_limit, requested_limit, int(rerank_top_k or self.reranker.top_k_default))
            pool_limit = min(pool_limit, self.reranker.max_candidates)
        results = self._backend_search(query=query, filters=filters, limit=pool_limit, force_hybrid=force_hybrid)
        results = _dedupe_and_filter_results(results)
        results = _apply_user_facing_quality_policies(results, query=query)
        reranked = False
        if do_rerank and results:
            before = list(results)
            results = self.reranker.rerank(query=query, results=results, top_k=rerank_top_k)
            results = _dedupe_and_filter_results(results)
            results = _apply_user_facing_quality_policies(results, query=query)
            reranked = results != before
        final_results = results[:requested_limit]
        if return_meta:
            reranker_available = self.reranker.is_available() if do_rerank else self.reranker.is_available(load=False)
            backend_meta = {}
            if results:
                first = results[0]
                backend_meta = {"search_mode": first.get("_search_mode"), "hybrid_strategy": first.get("_hybrid_strategy")}
            return {
                "results": final_results,
                "meta": {
                    "backend": self.backend_name,
                    "reranked": do_rerank and reranker_available and bool(results),
                    "candidate_pool_size": pool_limit,
                    "rerank_top_k": int(rerank_top_k or self.reranker.top_k_default) if do_rerank else None,
                    "reranker_available": reranker_available,
                    "rerank_reordered": reranked,
                    **{k: v for k, v in backend_meta.items() if v},
                },
            }
        return final_results

    def search_by_vector(
        self,
        *,
        query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = None,
    ) -> List[Dict[str, Any]]:
        requested_limit = limit or getattr(self.backend, "default_limit", 20)
        if not hasattr(self.backend, "search_by_vector"):
            raise RuntimeError(f"Backend '{self.backend_name}' ne supporte pas search_by_vector")
        out = self.backend.search_by_vector(query_vector=query_vector, filters=filters, limit=requested_limit)
        out = _dedupe_and_filter_results(out)
        out = _apply_user_facing_quality_policies(out)
        return out[:requested_limit]
