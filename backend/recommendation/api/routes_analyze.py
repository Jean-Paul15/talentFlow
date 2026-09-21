# Routes d'analyse et matching

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from api.schemas import MatchRequest, MatchResponse, ScoreDetail
from api.schemas import CVImprovementRequest, CVImprovementResponse
from core.cv_storage import cv_storage
from core.es_client import es_client
from core.cv_analysis_cache import CVAnalysisCache
from core.rate_limiter import limiter, get_rate_limit
from services.rag_service import RAGService
from redis import Redis

router = APIRouter(prefix="/analyze", tags=["analyze"])

# Services singletons
_rag_service = None
_cache = None
_redis = None


def get_rag_service() -> RAGService:
    """Retourne le service RAG singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_cache() -> CVAnalysisCache:
    """Retourne cache Redis singleton."""
    global _cache, _redis
    if _cache is None:
        _redis = Redis.from_url("redis://redis:6379/0")
        _cache = CVAnalysisCache(_redis)
    return _cache


@router.post("/match", response_model=MatchResponse)
@limiter.limit("50/minute")  # 50 req/min pour endpoint coûteux
async def analyze_match(
    request: MatchRequest,
    request_obj=None,  # slowapi injecte Request automatiquement
) -> MatchResponse:
    """Analyse la correspondance CV vs Offre avec cache Redis."""
    cache = get_cache()
    
    # Vérifier cache d'abord
    cached = await cache.get(request.cv_id, request.job_id)
    if cached:
        logger.info(f"Returning cached analysis for {request.cv_id} vs {request.job_id}")
        return MatchResponse(**cached)
    
    # Récupérer CV
    cv_data = cv_storage.get_cached(request.cv_id)
    if not cv_data:
        raise HTTPException(404, "CV non trouve")
    
    # Récupérer offre
    job_data = es_client.get_job(request.job_id)
    if not job_data:
        raise HTTPException(404, "Offre non trouvee")
    
    # Analyser
    service = get_rag_service()
    result = service.analyze_match(cv_data, job_data)
    
    response = MatchResponse(
        scores=ScoreDetail(**result["scores"]),
        analysis=result["analysis"],
        job=result["job"],
    )
    
    # Stocker dans cache
    await cache.set(request.cv_id, request.job_id, response.dict())
    
    return response


@router.post("/improve-cv", response_model=CVImprovementResponse)
@limiter.limit("30/minute")  # 30 req/min pour LLM (très coûteux)
async def improve_cv(
    request: CVImprovementRequest,
    request_obj=None,
) -> CVImprovementResponse:
    """Suggestions d'amélioration du CV (rate limited)."""
    cv_data = cv_storage.get_cached(request.cv_id)
    if not cv_data:
        raise HTTPException(404, "CV non trouve")
    
    job_data = es_client.get_job(request.job_id)
    if not job_data:
        raise HTTPException(404, "Offre non trouvee")
    
    service = get_rag_service()
    suggestions = service.improve_cv(cv_data, job_data)
    
    return CVImprovementResponse(suggestions=suggestions)
