"""Facade implementation aggregator."""

from __future__ import annotations

from .backend_impl import QdrantSearchBackend, _project_vectors_2d, _truncate_text
from .facade_base import HybridSearchServiceBaseMixin
from .facade_compare import HybridSearchServiceCompareMixin
from .facade_meta import HybridSearchServiceMetaMixin
from .facade_search import HybridSearchServiceSearchMixin
from .filters_impl import _canonicalize_url, _dedupe_and_filter_results, _env, _env_float, _is_probable_non_job_result, _normalize_space, _to_plain_list
from .ranking import _apply_user_facing_quality_policies, _coerce_float, _freshness_multiplier, _quality_multiplier


class HybridSearchService(
    HybridSearchServiceBaseMixin,
    HybridSearchServiceSearchMixin,
    HybridSearchServiceCompareMixin,
    HybridSearchServiceMetaMixin,
):
    """Search facade used by the existing call sites."""


__all__ = [
    "HybridSearchService",
    "QdrantSearchBackend",
    "_apply_user_facing_quality_policies",
    "_canonicalize_url",
    "_coerce_float",
    "_dedupe_and_filter_results",
    "_env",
    "_env_float",
    "_freshness_multiplier",
    "_is_probable_non_job_result",
    "_normalize_space",
    "_project_vectors_2d",
    "_quality_multiplier",
    "_to_plain_list",
    "_truncate_text",
]
