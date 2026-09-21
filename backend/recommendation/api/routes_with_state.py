# Endpoints FastAPI avec state manager temps réel
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel, Field

from ..core.rag_service_complete import RAGServiceComplete
from ..core.state_manager import analysis_state_manager, AnalysisStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cv", tags=["Analysis"])

# Service RAG avec OutputParsers + State Manager
rag_service = RAGServiceComplete()


# ============================================================================
# REQUÊTES
# ============================================================================

class GapAnalysisRequest(BaseModel):
    """Demande analyse gaps"""
    cv_text: str = Field(..., min_length=50, max_length=5000)
    job_title: str = Field(..., min_length=3, max_length=100)
    company: str = Field(default="Unknown", max_length=100)
    job_description: Optional[str] = Field(default="N/A", max_length=2000)
    required_skills: Optional[str] = Field(default="N/A", max_length=500)
    match_score: float = Field(default=75.0, ge=0, le=100)


class CVImprovementRequest(BaseModel):
    """Demande amélioration CV"""
    cv_text: str = Field(..., min_length=50, max_length=5000)
    job_title: str = Field(..., min_length=3, max_length=100)
    required_skills: Optional[str] = Field(default="N/A", max_length=500)


class JobExplanationRequest(BaseModel):
    """Demande explication offre"""
    job_title: str = Field(..., min_length=3, max_length=100)
    company: str = Field(default="Unknown", max_length=100)
    job_description: Optional[str] = Field(default="N/A", max_length=2000)
    required_skills: Optional[str] = Field(default="N/A", max_length=500)
    experience_years: int = Field(default=3, ge=0, le=50)


class AnalysisStateResponse(BaseModel):
    """Réponse état d'une analyse"""
    task_id: str
    status: str  # pending, processing, completed, failed
    step: str    # validation, extraction, analysis, formatting, completed
    progress: int  # 0-100
    message: str
    partial_result: Optional[Dict[str, Any]] = None  # Résultat partiel temps réel
    final_result: Optional[Dict[str, Any]] = None    # Résultat final
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ============================================================================
# ENDPOINT 1: Démarrer analyse avec état temps réel
# ============================================================================

@router.post("/gaps/async", response_model=Dict)
async def analyze_gaps_async(
    request: GapAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Lance analyse gaps ASYNCHRONE avec tracking état.
    
    Retourne immédiatement task_id
    Frontend poll /api/cv/state/{task_id} pour le progression
    WebSocket peut s'abonner pour mises à jour temps réel
    OutputParser force JSON structuré
    LLM Factory = changeable dynamiquement
    
    Example:
        POST /api/cv/gaps/async
        {
            "cv_text": "Développeur Python...",
            "job_title": "Senior Backend",
            "company": "TechCorp"
        }
        
        Response:
        {
            "task_id": "task_abc123def456",
            "status": "processing"
        }
        
        # Ensuite faire:
        GET /api/cv/state/task_abc123def456
        # Retourne progress, partial_result, etc
    """
    try:
        # Crée task et reçoit task_id
        task_id = analysis_state_manager.create_analysis(
            analysis_type="gap_analysis",
            user_id="unknown"  # TODO: Obtenir de JWT
        )
        
        # Lance traitement en arrière-plan (async)
        background_tasks.add_task(
            rag_service.analyze_gaps_with_state,
            cv_text=request.cv_text,
            job_title=request.job_title,
            task_id=task_id,
            company=request.company,
            job_description=request.job_description or "N/A",
            required_skills=request.required_skills or "N/A",
            match_score=request.match_score
        )
        
        logger.info(f"Gap analysis async started: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Analyse en cours. Consulte /api/cv/state/{task_id} pour progression"
        }
        
    except Exception as e:
        logger.error(f"Erreur création analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improve-cv/async", response_model=Dict)
async def improve_cv_async(
    request: CVImprovementRequest,
    background_tasks: BackgroundTasks
):
    """Lance amélioration CV asynchrone avec tracking état"""
    try:
        task_id = analysis_state_manager.create_analysis(
            analysis_type="cv_improvement",
            user_id="unknown"
        )
        
        background_tasks.add_task(
            rag_service.improve_cv_with_state,
            cv_text=request.cv_text,
            job_title=request.job_title,
            task_id=task_id,
            required_skills=request.required_skills or "N/A"
        )
        
        logger.info(f"CV improvement async started: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain-job/async", response_model=Dict)
async def explain_job_async(
    request: JobExplanationRequest,
    background_tasks: BackgroundTasks
):
    """Lance explication offre asynchrone avec tracking état"""
    try:
        task_id = analysis_state_manager.create_analysis(
            analysis_type="job_explanation",
            user_id="unknown"
        )
        
        background_tasks.add_task(
            rag_service.explain_job_with_state,
            job_title=request.job_title,
            task_id=task_id,
            company=request.company,
            job_description=request.job_description or "N/A",
            required_skills=request.required_skills or "N/A",
            experience_years=request.experience_years
        )
        
        logger.info(f"Job explanation async started: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 2: Récupérer état d'une analyse (POLLING)
# ============================================================================

@router.get("/state/{task_id}", response_model=AnalysisStateResponse)
async def get_analysis_state(task_id: str):
    """
    Récupère état courant d'une analyse.
    
    Frontend poll cet endpoint toutes les 500ms
    Retourne progress 0-100
    Retourne partial_result (mis à jour en temps réel)
    Retourne final_result une fois terminé
    
    Example:
        GET /api/cv/state/task_abc123def456
        
        Response (en cours):
        {
            "task_id": "task_abc123def456",
            "status": "processing",
            "progress": 45,
            "step": "extraction",
            "message": "Extraction des compétences...",
            "partial_result": {
                "skills": ["Python", "FastAPI"]
            }
        }
        
        Response (terminé):
        {
            "task_id": "task_abc123def456",
            "status": "completed",
            "progress": 100,
            "final_result": {
                "points_forts": [...],
                "recommendation": "Oui",
                ...
            }
        }
    """
    state_dict = analysis_state_manager.get_state_dict(task_id)
    
    if not state_dict:
        raise HTTPException(status_code=404, detail=f"Analyse non trouvée: {task_id}")
    
    return AnalysisStateResponse(**state_dict)


# ============================================================================
# ENDPOINT 3: WebSocket (TEMPS RÉEL)
# ============================================================================

from fastapi import WebSocket

@router.websocket("/ws/state/{task_id}")
async def websocket_analysis_state(websocket: WebSocket, task_id: str):
    """
    WebSocket pour mises à jour TEMPS RÉEL (meilleur que polling).
    
    Connexion persiste tant que l'analyse est en cours
    Reçoit updates JSON à chaque changement d'état
    Ferme automatiquement quand analyse terminée
    Réduit bande passante vs polling
    
    Example (JavaScript/React):
        const ws = new WebSocket('ws://backend:8001/api/cv/ws/state/task_abc123');
        
        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            console.log(`Progress: ${update.progress}%`);
            console.log(`Message: ${update.message}`);
            
            if (update.status === 'completed') {
                console.log('Résultat:', update.final_result);
            }
        };
    """
    await websocket.accept()
    
    state = analysis_state_manager.get_state(task_id)
    if not state:
        await websocket.send_json({
            "error": f"Analyse non trouvée: {task_id}"
        })
        await websocket.close(code=1008)
        return
    
    # Callback WebSocket pour mises à jour temps réel
    async def on_state_update(update):
        try:
            await websocket.send_json(update.dict())
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
    
    # S'abonne aux mises à jour
    analysis_state_manager.subscribe_websocket(task_id, on_state_update)
    
    try:
        # Reste connecté jusqu'à fin analyse
        while True:
            # Attend message ou timeout
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            
            # Peut recevoir cancel command
            msg = {"message": "Websocket actif"}
            await websocket.send_json(msg)
            
    except asyncio.TimeoutError:
        logger.info(f"WebSocket timeout: {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Se désabonne
        analysis_state_manager.unsubscribe_websocket(task_id, on_state_update)
        await websocket.close()


# ============================================================================
# ENDPOINT 4: Endpoints SYNCHRONES (compatibilité - pas de state)
# ============================================================================

@router.post("/gaps", response_model=Dict)
async def analyze_gaps_sync(request: GapAnalysisRequest):
    """Analyse gaps synchrone (réponse immédiate, pas de state)"""
    try:
        result = await rag_service.analyze_gaps(
            cv_text=request.cv_text,
            job_title=request.job_title,
            company=request.company,
            job_description=request.job_description or "N/A",
            required_skills=request.required_skills or "N/A",
            match_score=request.match_score
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improve-cv", response_model=Dict)
async def improve_cv_sync(request: CVImprovementRequest):
    """Amélioration CV synchrone"""
    try:
        result = await rag_service.improve_cv(
            cv_text=request.cv_text,
            job_title=request.job_title,
            required_skills=request.required_skills or "N/A"
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain-job", response_model=Dict)
async def explain_job_sync(request: JobExplanationRequest):
    """Explication offre synchrone"""
    try:
        result = await rag_service.explain_job(
            job_title=request.job_title,
            company=request.company,
            job_description=request.job_description or "N/A",
            required_skills=request.required_skills or "N/A",
            experience_years=request.experience_years
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
