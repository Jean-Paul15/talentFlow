from __future__ import annotations

from services.rerank_policy_service import RerankPolicyService
from services.search_service import HybridSearchService

_search_service: HybridSearchService | None = None
_rerank_policy: RerankPolicyService | None = None


def get_search_service() -> HybridSearchService:
    global _search_service
    if _search_service is None:
        _search_service = HybridSearchService()
    return _search_service


def get_rerank_policy() -> RerankPolicyService:
    global _rerank_policy
    service = get_search_service()
    if _rerank_policy is None:
        _rerank_policy = RerankPolicyService(
            initial_enabled=bool(service.reranker.enabled_by_default),
        )
    _rerank_policy.bind_reranker(service.reranker)
    return _rerank_policy
