from __future__ import annotations

from fastapi import APIRouter

from api.schemas import RerankPolicyManualRequest, RerankPolicySettingsRequest, RerankPolicyStateResponse
from services.runtime_state import get_rerank_policy

from .common import as_http_500

router = APIRouter()


@router.get('/rerank-policy', response_model=RerankPolicyStateResponse)
async def rerank_policy_state(history_limit: int = 20) -> RerankPolicyStateResponse:
    try:
        return RerankPolicyStateResponse(**get_rerank_policy().get_state(history_limit=history_limit))
    except Exception as err:
        raise as_http_500(err, 'rerank policy state')


@router.post('/rerank-policy/manual', response_model=RerankPolicyStateResponse)
async def rerank_policy_manual(request: RerankPolicyManualRequest) -> RerankPolicyStateResponse:
    try:
        return RerankPolicyStateResponse(**get_rerank_policy().set_manual(enabled=bool(request.enabled)))
    except Exception as err:
        raise as_http_500(err, 'rerank policy manual')


@router.post('/rerank-policy/auto', response_model=RerankPolicyStateResponse)
async def rerank_policy_auto() -> RerankPolicyStateResponse:
    try:
        return RerankPolicyStateResponse(**get_rerank_policy().set_auto())
    except Exception as err:
        raise as_http_500(err, 'rerank policy auto')


@router.post('/rerank-policy/settings', response_model=RerankPolicyStateResponse)
async def rerank_policy_settings(request: RerankPolicySettingsRequest) -> RerankPolicyStateResponse:
    try:
        state = get_rerank_policy().update_settings(
            target_ndcg_k=request.target_ndcg_k,
            min_cases_for_decision=request.min_cases_for_decision,
            enable_ndcg_gain_abs=request.enable_ndcg_gain_abs,
            enable_mrr_gain_abs=request.enable_mrr_gain_abs,
            disable_ndcg_gain_abs=request.disable_ndcg_gain_abs,
            disable_mrr_gain_abs=request.disable_mrr_gain_abs,
            enable_windows=request.enable_windows,
            disable_windows=request.disable_windows,
        )
        return RerankPolicyStateResponse(**state)
    except Exception as err:
        raise as_http_500(err, 'rerank policy settings')
