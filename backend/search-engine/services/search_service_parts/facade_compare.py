"""Comparison helpers for the hybrid search facade."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .filters_impl import _dedupe_and_filter_results
from .ranking import _apply_user_facing_quality_policies


class HybridSearchServiceCompareMixin:
    def compare_rerank(
        self,
        *,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        rerank_top_k: Optional[int] = None,
        candidate_pool_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        requested_limit = limit or getattr(self.backend, "default_limit", 20)
        pool_limit = candidate_pool_size or max(requested_limit, int(rerank_top_k or self.reranker.top_k_default))
        pool_limit = min(pool_limit, self.reranker.max_candidates)
        baseline = self._backend_search(query=query, filters=filters, limit=pool_limit)
        baseline = _dedupe_and_filter_results(baseline)
        baseline = _apply_user_facing_quality_policies(baseline, query=query)
        reranked = self.reranker.rerank(query=query, results=[dict(r) for r in baseline], top_k=rerank_top_k)
        reranked = _dedupe_and_filter_results(reranked)
        reranked = _apply_user_facing_quality_policies(reranked, query=query)
        return {
            "backend": self.backend_name,
            "baseline": baseline[:requested_limit],
            "reranked": reranked[:requested_limit],
            "candidate_pool_size": pool_limit,
            "rerank_top_k": int(rerank_top_k or self.reranker.top_k_default),
            "reranker_available": self.reranker.is_available(),
        }

    def compare_modes(
        self,
        *,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        rerank_top_k: Optional[int] = None,
        candidate_pool_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        requested_limit = limit or getattr(self.backend, "default_limit", 20)
        pool_limit = candidate_pool_size or max(requested_limit, int(rerank_top_k or self.reranker.top_k_default))
        pool_limit = min(pool_limit, self.reranker.max_candidates)
        dense = self._backend_search(query=query, filters=filters, limit=pool_limit, force_hybrid=False)
        dense = _dedupe_and_filter_results(dense)
        dense = _apply_user_facing_quality_policies(dense, query=query)
        hybrid = self._backend_search(query=query, filters=filters, limit=pool_limit, force_hybrid=True)
        hybrid = _dedupe_and_filter_results(hybrid)
        hybrid = _apply_user_facing_quality_policies(hybrid, query=query)
        hybrid_reranked = self.reranker.rerank(query=query, results=[dict(r) for r in hybrid], top_k=rerank_top_k)
        hybrid_reranked = _dedupe_and_filter_results(hybrid_reranked)
        hybrid_reranked = _apply_user_facing_quality_policies(hybrid_reranked, query=query)
        return {
            "backend": self.backend_name,
            "dense": dense[:requested_limit],
            "hybrid": hybrid[:requested_limit],
            "hybrid_reranked": hybrid_reranked[:requested_limit],
            "candidate_pool_size": pool_limit,
            "rerank_top_k": int(rerank_top_k or self.reranker.top_k_default),
            "reranker_available": self.reranker.is_available(load=False),
        }
