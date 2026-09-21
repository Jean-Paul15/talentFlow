# Helper for state-managed analysis - Extrait logique répétitive
import logging
import asyncio
from .state_manager import analysis_state_manager, AnalysisStatus, AnalysisStep
from .retry_logic import with_retry
from .metrics import track_analysis_metrics

logger = logging.getLogger(__name__)


async def execute_with_state(
    task_id: str,
    analysis_type: str,
    chain_fn,
    chain_params: dict,
    validation_fn=None
):
    """Execute analysis chain avec state tracking temps réel
    
    Centralise la logique 5 étapes répétitive:
    1. Validation (10%)
    2. Extraction (40%)
    3. Analysis (70%)
    4. Formatting (90%)
    5. Completion (100%)
    
    Args:
        task_id: ID de la task (pour tracking)
        analysis_type: "gap_analysis" | "cv_improvement" | "job_explanation"
        chain_fn: Callable (chain.ainvoke)
        chain_params: Dict des params pour chain
        validation_fn: Optional callable pour validation custom
        
    Returns:
        Result object (GapAnalysisOutput | CVImprovementOutput | JobExplanationOutput)
        
    Example:
        result = await execute_with_state(
            task_id=task_id,
            analysis_type="gap_analysis",
            chain_fn=self.gap_chain.ainvoke,
            chain_params={
                "cv_text": "...",
                "job_title": "..."
            },
            validation_fn=lambda: validate_cv_text(...)
        )
    """
    try:
        # Étape 1: Validation (10%)
        await analysis_state_manager.update_state(
            task_id=task_id,
            status=AnalysisStatus.PROCESSING,
            step=AnalysisStep.VALIDATION,
            progress=10,
            message="Validation des données..."
        )
        
        if validation_fn:
            validation_fn()
        await asyncio.sleep(0.05)
        
        # Étape 2: Extraction (40%)
        await analysis_state_manager.update_state(
            task_id=task_id,
            step=AnalysisStep.EXTRACTION,
            progress=40,
            message="Extraction et préparation..."
        )
        await asyncio.sleep(0.05)
        
        # Étape 3: Analyse LLM (70%)
        await analysis_state_manager.update_state(
            task_id=task_id,
            step=AnalysisStep.ANALYSIS,
            progress=70,
            message="Traitement par LLM en cours..."
        )
        
        logger.info(f"Analysis start: {analysis_type} - {task_id}")
        
        # Appel LLM avec retry + timeout automatique
        @with_retry(max_attempts=3, timeout=30.0)
        async def _call_llm():
            return await chain_fn(chain_params)
        
        result = await _call_llm()
        
        # Étape 4: Formatage (90%)
        await analysis_state_manager.update_state(
            task_id=task_id,
            step=AnalysisStep.FORMATTING,
            progress=90,
            message="Formatage de la réponse...",
            partial_result=result.model_dump()
        )
        
        # Étape 5: Complétude (100%)
        final_result = result.model_dump()
        analysis_state_manager.set_final_result(task_id, final_result)
        
        await analysis_state_manager.update_state(
            task_id=task_id,
            step=AnalysisStep.COMPLETED,
            progress=100,
            message="Analyse complétée"
        )
        
        logger.info(f"Analysis complete: {analysis_type} - {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Analysis error: {analysis_type} - {task_id} - {e}")
        analysis_state_manager.set_error(task_id, str(e))
        raise
