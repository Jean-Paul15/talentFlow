# Gestionnaire d'états global (singleton)
import logging
from typing import Optional, Dict, List, Callable
from uuid import uuid4
from .analysis_state import AnalysisState

logger = logging.getLogger(__name__)


class AnalysisStateManager:
    """Gestionnaire d'états pour toutes les analyses"""
    
    _instance = None
    _states: Dict[str, AnalysisState] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_analysis(self, analysis_type: str, user_id: str) -> str:
        """Crée une analyse et retourne task_id"""
        task_id = f"task_{uuid4().hex[:16]}"
        state = AnalysisState(task_id, analysis_type, user_id)
        self._states[task_id] = state
        logger.info(f"Analyse créée: {task_id} (type={analysis_type})")
        return task_id
    
    def get_state(self, task_id: str) -> Optional[AnalysisState]:
        """Récupère état d'une analyse"""
        return self._states.get(task_id)
    
    def get_state_dict(self, task_id: str) -> Optional[Dict]:
        """Récupère état sérialisé pour GraphQL"""
        state = self._states.get(task_id)
        return state.to_dict() if state else None
    
    async def update_state(
        self,
        task_id: str,
        status=None,
        step=None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        partial_result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Met à jour état d'une analyse"""
        state = self._states.get(task_id)
        if not state:
            logger.warning(f"Analyse non trouvée: {task_id}")
            return
        
        await state.update(
            status=status,
            step=step,
            progress=progress,
            message=message,
            partial_result=partial_result,
            error=error
        )
    
    def set_final_result(self, task_id: str, result: Dict):
        """Enregistre le résultat final"""
        state = self._states.get(task_id)
        if state:
            state.final_result = result
            from .analysis_state import AnalysisStatus
            state.status = AnalysisStatus.COMPLETED
            state.progress = 100
            logger.info(f"Analyse complétée: {task_id}")
    
    def set_error(self, task_id: str, error: str):
        """Enregistre une erreur"""
        state = self._states.get(task_id)
        if state:
            state.error = error
            from .analysis_state import AnalysisStatus
            state.status = AnalysisStatus.FAILED
            logger.error(f"Analyse échouée: {task_id} - {error}")
    
    def subscribe_websocket(self, task_id: str, callback: Callable):
        """S'abonne aux mises à jour temps réel"""
        state = self._states.get(task_id)
        if state:
            state.subscribers.append(callback)
            logger.info(f"WebSocket abonné: {task_id}")
    
    def unsubscribe_websocket(self, task_id: str, callback: Callable):
        """Se désabonne des mises à jour"""
        state = self._states.get(task_id)
        if state and callback in state.subscribers:
            state.subscribers.remove(callback)
            logger.info(f"WebSocket désabonné: {task_id}")
    
    def cleanup(self, task_id: str):
        """Supprime une analyse"""
        if task_id in self._states:
            del self._states[task_id]
            logger.info(f"Analyse supprimée: {task_id}")
    
    def get_user_analyses(self, user_id: str) -> List[Dict]:
        """Retourne toutes les analyses d'un utilisateur"""
        return [
            state.to_dict()
            for state in self._states.values()
            if state.user_id == user_id
        ]


# Singleton global
analysis_state_manager = AnalysisStateManager()


# ============================================================================
# UTILISATION DANS LES SERVICES
# ============================================================================

"""
# rag_service_with_state.py

from .state_manager import (
    analysis_state_manager,
    AnalysisStatus,
    AnalysisStep
)

class RAGServiceWithState:
    async def analyze_gaps_with_updates(
        self,
        cv_text: str,
        job_title: str,
        task_id: str  # Reçu de FastAPI
    ) -> Dict:
        '''Analyse avec mises à jour temps réel'''
        
        try:
            # Étape 1: Validation
            await analysis_state_manager.update_state(
                task_id=task_id,
                status=AnalysisStatus.PROCESSING,
                step=AnalysisStep.VALIDATION,
                progress=10,
                message="Validation du CV..."
            )
            await asyncio.sleep(0.5)
            
            # Étape 2: Extraction
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.EXTRACTION,
                progress=40,
                message="Extraction des compétences..."
            )
            result_partial = {"skills": ["Python", "FastAPI"]}
            await analysis_state_manager.update_state(
                task_id=task_id,
                partial_result=result_partial
            )
            
            # Étape 3: Analyse LLM
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.ANALYSIS,
                progress=70,
                message="Analyse LLM en cours..."
            )
            result = await self.gap_chain.ainvoke({...})
            
            # Étape 4: Formatage
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.FORMATTING,
                progress=90,
                message="Formatage de la réponse..."
            )
            
            # Résultat final
            final_result = result.dict()
            analysis_state_manager.set_final_result(task_id, final_result)
            
            return final_result
            
        except Exception as e:
            analysis_state_manager.set_error(task_id, str(e))
            raise
"""
