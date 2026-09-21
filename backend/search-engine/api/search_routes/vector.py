from __future__ import annotations

from fastapi import APIRouter

from api.schemas import JobResult, SearchResponse, VectorSearchRequest
from services.runtime_state import get_search_service

from .common import as_http_500, build_filters

router = APIRouter()


@router.post('/by-vector', response_model=SearchResponse)
async def search_jobs_by_vector(request: VectorSearchRequest) -> SearchResponse:
    try:
        service = get_search_service()
        filters = build_filters(request.location, request.contract_type, request.skills)
        results = service.search_by_vector(
            query_vector=request.query_vector,
            filters=filters if filters else None,
            limit=request.limit,
        )
        search_mode = results[0].get('_search_mode') if results else 'semantic_vector'
        hybrid_strategy = results[0].get('_hybrid_strategy') if results else None
        return SearchResponse(
            query='[vector]',
            total=len(results),
            results=[JobResult(**r) for r in results],
            backend=service.backend_name,
            reranked=False,
            search_mode=search_mode,
            hybrid_strategy=hybrid_strategy,
        )
    except Exception as err:
        raise as_http_500(err, 'recherche by-vector')


@router.get('/vector-preview')
async def vector_preview(
    limit: int = 120,
    source_name: str | None = None,
    country: str | None = None,
):
    try:
        service = get_search_service()
        return service.vector_preview(limit=limit, source_name=source_name, country=country)
    except Exception as err:
        raise as_http_500(err, 'vector preview')


@router.get('/suggest')
async def suggest_skills(query: str, limit: int = 10):
    return {'suggestions': []}
