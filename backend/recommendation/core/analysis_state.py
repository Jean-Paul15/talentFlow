# État d'une analyse individuelle (< 100 lignes)
import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

logger = logging.getLogger(__name__)


class AnalysisStatus(str, Enum):
    """États d'une analyse"""
    PENDING = "pending"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisStep(str, Enum):
    """Étapes du traitement"""
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    FORMATTING = "formatting"
    COMPLETED = "completed"


class AnalysisStateUpdate(BaseModel):
    """Update d'état temps réel"""
    task_id: str
    status: AnalysisStatus
    step: AnalysisStep
    progress: int = Field(..., ge=0, le=100)
    message: str
    partial_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisState:
    """État d'une analyse (en mémoire)"""
    
    def __init__(self, task_id: str, analysis_type: str, user_id: str):
        self.task_id = task_id
        self.analysis_type = analysis_type
        self.user_id = user_id
        
        self.status = AnalysisStatus.PENDING
        self.step = AnalysisStep.VALIDATION
        self.progress = 0
        self.message = "En attente de traitement"
        self.partial_result: Optional[Dict] = None
        self.final_result: Optional[Dict] = None
        self.error: Optional[str] = None
        
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.subscribers: List[Callable] = []
    
    def to_dict(self) -> Dict:
        """Sérialiser pour GraphQL"""
        return {
            "task_id": self.task_id,
            "analysis_type": self.analysis_type,
            "user_id": self.user_id,
            "status": self.status.value,
            "step": self.step.value,
            "progress": self.progress,
            "message": self.message,
            "partial_result": self.partial_result,
            "final_result": self.final_result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AnalysisState":
        """Désérialiser depuis Redis"""
        state = cls(
            task_id=data["task_id"],
            analysis_type=data["analysis_type"],
            user_id=data["user_id"]
        )
        state.status = AnalysisStatus(data["status"])
        state.step = AnalysisStep(data["step"])
        state.progress = data["progress"]
        state.message = data["message"]
        state.partial_result = data.get("partial_result")
        state.final_result = data.get("final_result")
        state.error = data.get("error")
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])
        return state
    
    async def update(
        self,
        status: Optional[AnalysisStatus] = None,
        step: Optional[AnalysisStep] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        partial_result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Met à jour l'état et notifie abonnés"""
        if status:
            self.status = status
        if step:
            self.step = step
        if progress is not None:
            self.progress = max(0, min(100, progress))
        if message:
            self.message = message
        if partial_result is not None:
            self.partial_result = partial_result
        if error:
            self.error = error
        
        self.updated_at = datetime.utcnow()
        
        # Notifier abonnés
        update = AnalysisStateUpdate(
            task_id=self.task_id,
            status=self.status,
            step=self.step,
            progress=self.progress,
            message=self.message,
            partial_result=self.partial_result,
            error=self.error
        )
        
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Erreur callback: {e}")
