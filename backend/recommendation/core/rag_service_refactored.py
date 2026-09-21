# RAG Service Refactored - Utilise state_helper pour réduire répétition
import logging
from .llm_factory import LLMFactory
from .state_manager import analysis_state_manager
from .state_helper import execute_with_state
from .metrics import track_analysis_metrics
from ..services.prompts_with_parser import (
    create_gap_analysis_chain,
    create_cv_improvement_chain,
    create_job_explanation_chain,
    GapAnalysisOutput,
    CVImprovementOutput,
    JobExplanationOutput
)

logger = logging.getLogger(__name__)


class RAGServiceRefactored:
    """Service RAG refactorisé - Sans code répétitif
    
    Utilise state_helper.execute_with_state() pour centraliser
    la logique 5 étapes (Validation → Extraction → Analysis → 
    Formatting → Completion).
    
    Réduit de 351 lignes → 180 lignes.
    """
    
    def __init__(self):
        """Initialise chains avec LLM dynamique"""
        self.llm = LLMFactory.get()
        self.gap_chain = create_gap_analysis_chain(self.llm)
        self.improvement_chain = create_cv_improvement_chain(self.llm)
        self.explanation_chain = create_job_explanation_chain(self.llm)
        logger.info(f"RAGService init (LLM={LLMFactory.get_provider()})")
    
    # AVEC STATE (Async + Tracking)
    
    @track_analysis_metrics("gap_analysis")
    async def analyze_gaps_with_state(
        self, cv_text: str, job_title: str, task_id: str,
        company: str = "Unknown", job_description: str = "N/A",
        required_skills: str = "N/A", match_score: float = 75.0
    ) -> GapAnalysisOutput:
        """Analyse gaps avec tracking état temps réel"""
        
        def validate():
            if len(cv_text) < 50:
                raise ValueError("CV trop court")
            if len(job_title) < 3:
                raise ValueError("Titre offre trop court")
        
        return await execute_with_state(
            task_id=task_id,
            analysis_type="gap_analysis",
            chain_fn=self.gap_chain.ainvoke,
            chain_params={
                "cv_text": cv_text[:5000],
                "job_title": job_title[:100],
                "company": company[:100],
                "job_description": job_description[:2000],
                "required_skills": required_skills[:500],
                "match_score": int(max(0, min(100, match_score)))
            },
            validation_fn=validate
        )
    
    @track_analysis_metrics("cv_improvement")
    async def improve_cv_with_state(
        self, cv_text: str, job_title: str, task_id: str,
        required_skills: str = "N/A"
    ) -> CVImprovementOutput:
        """Amélioration CV avec tracking état"""
        
        def validate():
            if len(cv_text) < 50:
                raise ValueError("CV trop court")
        
        return await execute_with_state(
            task_id=task_id,
            analysis_type="cv_improvement",
            chain_fn=self.improvement_chain.ainvoke,
            chain_params={
                "cv_text": cv_text[:5000],
                "job_title": job_title[:100],
                "required_skills": required_skills[:500]
            },
            validation_fn=validate
        )
    
    @track_analysis_metrics("job_explanation")
    async def explain_job_with_state(
        self, job_title: str, task_id: str,
        company: str = "Unknown", job_description: str = "N/A",
        required_skills: str = "N/A", experience_years: int = 3
    ) -> JobExplanationOutput:
        """Explication offre avec tracking état"""
        
        return await execute_with_state(
            task_id=task_id,
            analysis_type="job_explanation",
            chain_fn=self.explanation_chain.ainvoke,
            chain_params={
                "job_title": job_title[:100],
                "company": company[:100],
                "job_description": job_description[:2000],
                "required_skills": required_skills[:500],
                "experience_years": max(0, min(50, experience_years))
            }
        )
    
    # SANS STATE (Simple version)
    
    async def analyze_gaps(
        self, cv_text: str, job_title: str,
        company: str = "Unknown", job_description: str = "N/A",
        required_skills: str = "N/A", match_score: float = 75.0
    ) -> GapAnalysisOutput:
        """Analyse sans tracking état"""
        return await self.gap_chain.ainvoke({
            "cv_text": cv_text[:5000],
            "job_title": job_title[:100],
            "company": company[:100],
            "job_description": job_description[:2000],
            "required_skills": required_skills[:500],
            "match_score": int(max(0, min(100, match_score)))
        })
    
    async def improve_cv(
        self, cv_text: str, job_title: str,
        required_skills: str = "N/A"
    ) -> CVImprovementOutput:
        """Amélioration CV simple"""
        return await self.improvement_chain.ainvoke({
            "cv_text": cv_text[:5000],
            "job_title": job_title[:100],
            "required_skills": required_skills[:500]
        })
    
    async def explain_job(
        self, job_title: str,
        company: str = "Unknown", job_description: str = "N/A",
        required_skills: str = "N/A", experience_years: int = 3
    ) -> JobExplanationOutput:
        """Explication offre simple"""
        return await self.explanation_chain.ainvoke({
            "job_title": job_title[:100],
            "company": company[:100],
            "job_description": job_description[:2000],
            "required_skills": required_skills[:500],
            "experience_years": max(0, min(50, experience_years))
        })
