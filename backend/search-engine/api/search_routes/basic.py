from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import JobResult, SearchCompareResponse, SearchModeCompareResponse, SearchRequest, SearchResponse
from services.runtime_state import get_search_service

from .common import as_http_500, build_filters

router = APIRouter()


@router.post('/', response_model=SearchResponse)
async def search_jobs(request: SearchRequest) -> SearchResponse:
    try:
        service = get_search_service()
        filters = build_filters(request.location, request.contract_type, request.skills)
        search_out = service.search(
            query=request.query,
            filters=filters if filters else None,
            limit=request.limit,
            rerank=request.rerank,
            rerank_top_k=request.rerank_top_k,
            candidate_pool_size=request.candidate_pool_size,
            return_meta=True,
        )
        results = search_out['results']
        meta = search_out.get('meta', {})
        return SearchResponse(
            query=request.query,
            total=len(results),
            results=[JobResult(**r) for r in results],
            backend=meta.get('backend', 'qdrant'),
            reranked=bool(meta.get('reranked', False)),
            candidate_pool_size=meta.get('candidate_pool_size'),
            rerank_top_k=meta.get('rerank_top_k'),
            search_mode=meta.get('search_mode'),
            hybrid_strategy=meta.get('hybrid_strategy'),
        )
    except Exception as err:
        raise as_http_500(err, 'recherche')


@router.post('/compare-rerank', response_model=SearchCompareResponse)
async def compare_rerank(request: SearchRequest) -> SearchCompareResponse:
    try:
        service = get_search_service()
        filters = build_filters(request.location, request.contract_type, request.skills)
        out = service.compare_rerank(
            query=request.query,
            filters=filters if filters else None,
            limit=request.limit,
            rerank_top_k=request.rerank_top_k,
            candidate_pool_size=request.candidate_pool_size,
        )
        baseline = out.get('baseline', [])
        reranked = out.get('reranked', [])
        return SearchCompareResponse(
            query=request.query,
            backend=out.get('backend', 'qdrant'),
            baseline_total=len(baseline),
            reranked_total=len(reranked),
            candidate_pool_size=int(out.get('candidate_pool_size') or max(request.limit, 1)),
            rerank_top_k=int(out.get('rerank_top_k') or request.rerank_top_k or min(request.limit, 20)),
            baseline=[JobResult(**r) for r in baseline],
            reranked=[JobResult(**r) for r in reranked],
        )
    except Exception as err:
        raise as_http_500(err, 'compare rerank')


@router.post('/compare-modes', response_model=SearchModeCompareResponse)
async def compare_modes(request: SearchRequest) -> SearchModeCompareResponse:
    try:
        service = get_search_service()
        filters = build_filters(request.location, request.contract_type, request.skills)
        out = service.compare_modes(
            query=request.query,
            filters=filters if filters else None,
            limit=request.limit,
            rerank_top_k=request.rerank_top_k,
            candidate_pool_size=request.candidate_pool_size,
        )
        dense = out.get('dense', []) or []
        hybrid = out.get('hybrid', []) or []
        hybrid_reranked = out.get('hybrid_reranked', []) or []
        return SearchModeCompareResponse(
            query=request.query,
            backend=out.get('backend', service.backend_name),
            candidate_pool_size=int(out.get('candidate_pool_size') or max(request.limit, 1)),
            rerank_top_k=int(out.get('rerank_top_k') or request.rerank_top_k or min(request.limit, 20)),
            dense_total=len(dense),
            hybrid_total=len(hybrid),
            hybrid_reranked_total=len(hybrid_reranked),
            dense=[JobResult(**r) for r in dense],
            hybrid=[JobResult(**r) for r in hybrid],
            hybrid_reranked=[JobResult(**r) for r in hybrid_reranked],
        )
    except Exception as err:
        raise as_http_500(err, 'compare modes')
