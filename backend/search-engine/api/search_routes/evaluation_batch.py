from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    RankingMetrics,
    SearchEvalBatchCaseResult,
    SearchEvalBatchRequest,
    SearchEvalBatchResponse,
    SearchEvalBatchSummary,
)
from services.evaluation_service import evaluate_ranked_list, normalize_relevance
from services.runtime_state import get_rerank_policy, get_search_service

from .common import as_http_500, build_filters
from .evaluation_batch_helpers import mean_metrics, update_metric_accumulators

router = APIRouter()


@router.post('/evaluate-batch', response_model=SearchEvalBatchResponse)
async def evaluate_search_batch(request: SearchEvalBatchRequest) -> SearchEvalBatchResponse:
    try:
        service = get_search_service()
        case_results: list[SearchEvalBatchCaseResult] = []
        skipped = 0

        ndcg_baseline_acc: dict[str, float] = {}
        ndcg_rerank_acc: dict[str, float] = {}
        mrr_baseline_acc = 0.0
        mrr_rerank_acc = 0.0

        for case in request.cases:
            relevance = normalize_relevance(case.relevant_ids, case.graded_relevance)
            if not relevance:
                skipped += 1
                continue

            filters = build_filters(case.location, case.contract_type, case.skills)
            compare = service.compare_rerank(
                query=case.query,
                filters=filters if filters else None,
                limit=request.limit,
                rerank_top_k=request.rerank_top_k,
                candidate_pool_size=request.candidate_pool_size,
            )

            baseline = compare.get('baseline', [])
            reranked = compare.get('reranked', [])
            baseline_rank = RankingMetrics(**evaluate_ranked_list(baseline, relevance, request.k_values))
            reranked_rank = RankingMetrics(**evaluate_ranked_list(reranked, relevance, request.k_values))
            b_mrr, r_mrr = update_metric_accumulators(
                baseline_rank,
                reranked_rank,
                ndcg_baseline_acc,
                ndcg_rerank_acc,
            )
            mrr_baseline_acc += b_mrr
            mrr_rerank_acc += r_mrr

            case_results.append(
                SearchEvalBatchCaseResult(
                    query=case.query,
                    judged_count=len(relevance),
                    baseline=baseline_rank,
                    reranked=reranked_rank,
                    baseline_top_ids=[str(r.get('id')) for r in baseline[: request.limit] if r.get('id') is not None],
                    reranked_top_ids=[str(r.get('id')) for r in reranked[: request.limit] if r.get('id') is not None],
                )
            )

        evaluated = len(case_results)
        if evaluated <= 0:
            raise HTTPException(
                status_code=400,
                detail='Aucun cas évaluable (chaque cas doit fournir relevant_ids ou graded_relevance).',
            )

        metrics = mean_metrics(evaluated, ndcg_baseline_acc, ndcg_rerank_acc, mrr_baseline_acc, mrr_rerank_acc)
        sample_case_pool = request.candidate_pool_size or max(request.limit, 1)
        sample_rerank_top_k = request.rerank_top_k or min(request.limit, 20)

        summary_payload = SearchEvalBatchSummary(
            cases_total=len(request.cases),
            cases_evaluated=evaluated,
            cases_skipped=skipped,
            **metrics,
        )
        policy_state = get_rerank_policy().record_batch_evaluation(
            summary=summary_payload.model_dump(),
            backend=service.backend_name,
            cases_evaluated=evaluated,
            candidate_pool_size=int(sample_case_pool),
            rerank_top_k=int(sample_rerank_top_k),
        )

        return SearchEvalBatchResponse(
            backend=service.backend_name,
            candidate_pool_size=int(sample_case_pool),
            rerank_top_k=int(sample_rerank_top_k),
            k_values=[int(k) for k in request.k_values],
            summary=summary_payload,
            cases=case_results,
            rerank_policy=policy_state,
        )
    except HTTPException:
        raise
    except Exception as err:
        raise as_http_500(err, 'evaluation batch search')
