from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import RankingMetrics, SearchEvalRequest, SearchEvalResponse
from services.evaluation_service import evaluate_ranked_list, normalize_relevance
from services.runtime_state import get_search_service

from .common import as_http_500, build_filters

router = APIRouter()


@router.post('/evaluate', response_model=SearchEvalResponse)
async def evaluate_search(request: SearchEvalRequest) -> SearchEvalResponse:
    try:
        service = get_search_service()
        filters = build_filters(request.location, request.contract_type, request.skills)
        relevance = normalize_relevance(
            relevant_ids=request.relevant_ids,
            graded_relevance=request.graded_relevance,
        )
        if not relevance:
            raise HTTPException(
                status_code=400,
                detail="Fournir `relevant_ids` ou `graded_relevance` pour l'évaluation.",
            )

        compare = service.compare_rerank(
            query=request.query,
            filters=filters if filters else None,
            limit=request.limit,
            rerank_top_k=request.rerank_top_k,
            candidate_pool_size=request.candidate_pool_size,
        )
        baseline = compare.get('baseline', [])
        reranked = compare.get('reranked', [])
        baseline_metrics = evaluate_ranked_list(baseline, relevance, k_values=request.k_values)
        reranked_metrics = evaluate_ranked_list(reranked, relevance, k_values=request.k_values)

        return SearchEvalResponse(
            query=request.query,
            backend=compare.get('backend', service.backend_name),
            judged_count=len(relevance),
            candidate_pool_size=int(compare.get('candidate_pool_size') or max(request.limit, 1)),
            rerank_top_k=int(compare.get('rerank_top_k') or request.rerank_top_k or min(request.limit, 20)),
            baseline=RankingMetrics(**baseline_metrics),
            reranked=RankingMetrics(**reranked_metrics),
            baseline_ids=[str(r.get('id')) for r in baseline if r.get('id') is not None],
            reranked_ids=[str(r.get('id')) for r in reranked if r.get('id') is not None],
        )
    except HTTPException:
        raise
    except Exception as err:
        raise as_http_500(err, 'evaluation search')
