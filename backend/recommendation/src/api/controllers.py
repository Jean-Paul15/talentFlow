# Étape 4: Controllers - Route handling pur (sans logique)
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from ..schemas import *
from ..services.cv_service import CVAnalysisService, CVCacheManager
from ..services.matching_service import JobMatchingService
from ..services.gap_service import GapAnalysisService
from ..core.di import DIContainer
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["rag"])

def get_services():
    """Inject services"""
    di = DIContainer()
    return {
        "cv": CVAnalysisService(di.llm),
        "matching": JobMatchingService(di.embeddings, di.es),
        "gap": GapAnalysisService(di.llm),
        "cache": CVCacheManager(di.redis.connection())
    }

@router.get("/health", response_model=HealthResponse)
async def health():
    """Sante service"""
    di = DIContainer()
    return {
        "status": "healthy",
        "service": "RAG Engine",
        "gemini_ready": True,
        "model": "gemini"
    }

@router.post("/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(
    request: CVAnalysisRequest,
    services=Depends(get_services),
    background_tasks: BackgroundTasks = None
):
    """Analyse CV avec cache"""
    cached = services["cache"].get_analysis(request.user_id)
    if cached:
        return CVAnalysisResponse(**cached)
    
    try:
        result = await services["cv"].analyze(request.cv_text, request.user_id)
        
        # Cache async
        if background_tasks:
            background_tasks.add_task(
                services["cache"].set_analysis,
                request.user_id,
                result
            )
        
        return CVAnalysisResponse(**result)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-jobs", response_model=list[JobMatchResponse])
async def match_jobs(request: JobMatchRequest, services=Depends(get_services)):
    """Match jobs - semantic search"""
    try:
        return await services["matching"].match_jobs(
            request.cv_text,
            request.top_k,
            request.min_score
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gap-analysis", response_model=GapAnalysisResponse)
async def gap_analysis(request: GapAnalysisRequest, services=Depends(get_services)):
    """Analyse gaps competences"""
    try:
        return await services["gap"].analyze_gaps(
            request.cv_text,
            request.job_title
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
