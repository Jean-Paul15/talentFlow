# Endpoint Factory - Crée endpoints async avec pattern uniforme
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Type
from pydantic import BaseModel
import logging

from ..core.state_manager import analysis_state_manager
from ..core.rag_service_refactored import RAGServiceRefactored

logger = logging.getLogger(__name__)

rag_service = RAGServiceRefactored()


def create_async_analysis_endpoint(
    router: APIRouter,
    endpoint_path: str,
    analysis_type: str,
    rag_method_name: str,
    request_model: Type[BaseModel],
    description: str
):
    """Factory pour créer endpoints async avec état tracking
    
    Élimine pattern répétitif: create_analysis → background_task → return task_id
    
    Args:
        router: FastAPI APIRouter
        endpoint_path: e.g., "gaps" → becomes POST /api/cv/gaps/async
        analysis_type: "gap_analysis" | "cv_improvement" | "job_explanation"
        rag_method_name: Method name on RAGServiceRefactored with _with_state
        request_model: Pydantic model (GapAnalysisRequest, etc)
        description: Docstring pour API docs
    
    Example:
        create_async_analysis_endpoint(
            router=router,
            endpoint_path="gaps",
            analysis_type="gap_analysis",
            rag_method_name="analyze_gaps_with_state",
            request_model=GapAnalysisRequest,
            description="Analyse gaps entre CV et offre"
        )
    """
    
    @router.post(f"/{endpoint_path}/async", response_model=Dict)
    async def async_endpoint(
        request: request_model,
        background_tasks: BackgroundTasks
    ):
        f"""{description}
        
        Lance l'analyse de façon asynchrone avec tracking état.
        Frontend peut poller /api/cv/state/{{task_id}} pour progression.
        """
        try:
            # Crée task et obtient task_id
            task_id = analysis_state_manager.create_analysis(
                analysis_type=analysis_type,
                user_id="unknown"
            )
            
            # Récupère la méthode et lance en background
            rag_method = getattr(rag_service, rag_method_name)
            background_tasks.add_task(
                rag_method,
                task_id=task_id,
                **request.model_dump()
            )
            
            logger.info(f"{analysis_type} async started: {task_id}")
            
            return {
                "task_id": task_id,
                "status": "processing",
                "message": f"Analyse en cours. Consulte /api/cv/state/{task_id}"
            }
            
        except Exception as e:
            logger.error(f"Error creating {analysis_type}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return async_endpoint


def create_sync_analysis_endpoint(
    router: APIRouter,
    endpoint_path: str,
    rag_method_name: str,
    request_model: Type[BaseModel],
    description: str
):
    """Factory pour créer endpoints synchrones (réponse immédiate)
    
    Args:
        Similar to create_async_analysis_endpoint but method should be
        the simple version (without _with_state)
    """
    
    @router.post(f"/{endpoint_path}", response_model=Dict)
    async def sync_endpoint(request: request_model):
        f"""{description} - Réponse immédiate (pas de state tracking)."""
        try:
            rag_method = getattr(rag_service, rag_method_name)
            result = await rag_method(**request.model_dump())
            return result.model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return sync_endpoint
