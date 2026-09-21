# RAG Service complète - OutputParsers partout + Dynamic LLM + Real-time state
import logging
import asyncio
from typing import Optional, Dict
from .llm_factory import LLMFactory
from .state_manager import (
    analysis_state_manager,
    AnalysisStatus,
    AnalysisStep
)
from ..services.prompts_with_parser import (
    create_gap_analysis_chain,
    create_cv_improvement_chain,
    create_job_explanation_chain,
    GapAnalysisOutput,
    CVImprovementOutput,
    JobExplanationOutput
)

logger = logging.getLogger(__name__)


class RAGServiceComplete:
    """Service RAG avec:
    - OutputParsers partout (JSON structuré)
    - LLM Factory dynamique Gemini-only
    - Real-time state (temps réel pour GraphQL)
    - Async/await partout
    """
    
    def __init__(self):
        """Initialise chains avec LLM dynamique"""
        self.llm = LLMFactory.get()  # Obtient le runtime Gemini officiel
        
        # Chains avec OutputParsers (force JSON)
        self.gap_chain = create_gap_analysis_chain(self.llm)
        self.improvement_chain = create_cv_improvement_chain(self.llm)
        self.explanation_chain = create_job_explanation_chain(self.llm)
        
        logger.info(f"RAGService initialisé (LLM={LLMFactory.get_provider()})")
    
    # =========================================================================
    # 1. ANALYSE DES GAPS - Avec state manager
    # =========================================================================
    
    async def analyze_gaps_with_state(
        self,
        cv_text: str,
        job_title: str,
        task_id: str,
        company: str = "Unknown",
        job_description: str = "N/A",
        required_skills: str = "N/A",
        match_score: float = 75.0
    ) -> GapAnalysisOutput:
        """
        Analyse gaps avec mises à jour temps réel pour GraphQL/WebSocket.
        
        Args:
            cv_text: Texte du CV
            job_title: Titre du poste
            task_id: ID task (pour tracking état)
            company: Nom entreprise
            job_description: Description complète
            required_skills: Compétences requises
            match_score: Score matching 0-100
        
        Returns:
            GapAnalysisOutput structuré (JSON)
        
        Example:
            task_id = await state_manager.create_analysis(...)
            result = await rag.analyze_gaps_with_state(
                cv_text="...",
                job_title="...",
                task_id=task_id
            )
            # GraphQL a reçu updates temps réel via WebSocket
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
            
            # Valide entrées
            cv_text = cv_text[:5000]
            job_title = job_title[:100]
            company = company[:100]
            required_skills = str(required_skills)[:500]
            match_score = max(0, min(100, match_score))
            
            # Étape 2: Extraction (40%)
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.EXTRACTION,
                progress=40,
                message="Extraction des compétences..."
            )
            await asyncio.sleep(0.1)  # Simule travail
            
            # Étape 3: Analyse LLM (70%)
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.ANALYSIS,
                progress=70,
                message="Analyse par LLM en cours... (StreamingMode)"
            )
            
            logger.info(f"Gap analysis start: {task_id}")
            
            # Chain avec OutputParser (force GapAnalysisOutput)
            result: GapAnalysisOutput = await self.gap_chain.ainvoke({
                "cv_text": cv_text,
                "job_title": job_title,
                "company": company,
                "job_description": job_description[:2000],
                "required_skills": required_skills,
                "match_score": int(match_score)
            })
            
            # Étape 4: Formatage (90%)
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.FORMATTING,
                progress=90,
                message="Formatage de la réponse...",
                partial_result=result.model_dump()  # Résultat partiel temps réel
            )
            
            # Résultat final (100%)
            final_result = result.model_dump()
            analysis_state_manager.set_final_result(task_id, final_result)
            
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.COMPLETED,
                progress=100,
                message="Analyse complétée"
            )
            
            logger.info(f"Gap analysis complete: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Gap analysis error: {task_id} - {e}")
            analysis_state_manager.set_error(task_id, str(e))
            raise
    
    # =========================================================================
    # 2. AMÉLIORATION CV - Avec state manager
    # =========================================================================
    
    async def improve_cv_with_state(
        self,
        cv_text: str,
        job_title: str,
        task_id: str,
        required_skills: str = "N/A"
    ) -> CVImprovementOutput:
        """Amélioration CV avec mises à jour temps réel"""
        try:
            # Étape 1: Validation
            await analysis_state_manager.update_state(
                task_id=task_id,
                status=AnalysisStatus.PROCESSING,
                step=AnalysisStep.VALIDATION,
                progress=10,
                message="Validation du CV..."
            )
            
            cv_text = cv_text[:5000]
            job_title = job_title[:100]
            required_skills = str(required_skills)[:500]
            
            # Étape 2: Extraction
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.EXTRACTION,
                progress=40,
                message="Analyse du CV et de l'offre..."
            )
            
            # Étape 3: Analyse LLM
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.ANALYSIS,
                progress=70,
                message="Génération suggestions ATS..."
            )
            
            logger.info(f"CV improvement start: {task_id}")
            
            # Chain avec OutputParser
            result: CVImprovementOutput = await self.improvement_chain.ainvoke({
                "cv_text": cv_text,
                "job_title": job_title,
                "required_skills": required_skills
            })
            
            # Résultat final
            final_result = result.model_dump()
            analysis_state_manager.set_final_result(task_id, final_result)
            
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.COMPLETED,
                progress=100,
                message="Suggestions générées"
            )
            
            logger.info(f"CV improvement complete: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"CV improvement error: {task_id} - {e}")
            analysis_state_manager.set_error(task_id, str(e))
            raise
    
    # =========================================================================
    # 3. EXPLICATION OFFRE - Avec state manager
    # =========================================================================
    
    async def explain_job_with_state(
        self,
        job_title: str,
        task_id: str,
        company: str = "Unknown",
        job_description: str = "N/A",
        required_skills: str = "N/A",
        experience_years: int = 3
    ) -> JobExplanationOutput:
        """Explication offre avec mises à jour temps réel"""
        try:
            # Étape 1: Validation
            await analysis_state_manager.update_state(
                task_id=task_id,
                status=AnalysisStatus.PROCESSING,
                step=AnalysisStep.VALIDATION,
                progress=10,
                message="Validation de l'offre..."
            )
            
            job_title = job_title[:100]
            company = company[:100]
            required_skills = str(required_skills)[:500]
            experience_years = max(0, min(50, experience_years))
            
            # Étape 2: Extraction
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.EXTRACTION,
                progress=40,
                message="Analyse de l'offre d'emploi..."
            )
            
            # Étape 3: Analyse LLM
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.ANALYSIS,
                progress=70,
                message="Génération explication..."
            )
            
            logger.info(f"Job explanation start: {task_id}")
            
            # Chain avec OutputParser
            result: JobExplanationOutput = await self.explanation_chain.ainvoke({
                "job_title": job_title,
                "company": company,
                "job_description": job_description[:2000],
                "required_skills": required_skills,
                "experience_years": experience_years
            })
            
            # Résultat final
            final_result = result.model_dump()
            analysis_state_manager.set_final_result(task_id, final_result)
            
            await analysis_state_manager.update_state(
                task_id=task_id,
                step=AnalysisStep.COMPLETED,
                progress=100,
                message="Explication générée"
            )
            
            logger.info(f"Job explanation complete: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Job explanation error: {task_id} - {e}")
            analysis_state_manager.set_error(task_id, str(e))
            raise
    
    # =========================================================================
    # VERSION SIMPLE (sans state - pour compatibilité)
    # =========================================================================
    
    async def analyze_gaps(
        self,
        cv_text: str,
        job_title: str,
        company: str = "Unknown",
        job_description: str = "N/A",
        required_skills: str = "N/A",
        match_score: float = 75.0
    ) -> GapAnalysisOutput:
        """Analyse sans tracking état (version simple)"""
        try:
            cv_text = cv_text[:5000]
            job_title = job_title[:100]
            company = company[:100]
            required_skills = str(required_skills)[:500]
            match_score = max(0, min(100, match_score))
            
            result: GapAnalysisOutput = await self.gap_chain.ainvoke({
                "cv_text": cv_text,
                "job_title": job_title,
                "company": company,
                "job_description": job_description[:2000],
                "required_skills": required_skills,
                "match_score": int(match_score)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Gap analysis error: {e}")
            raise
    
    async def improve_cv(
        self,
        cv_text: str,
        job_title: str,
        required_skills: str = "N/A"
    ) -> CVImprovementOutput:
        """Amélioration CV sans tracking état"""
        try:
            cv_text = cv_text[:5000]
            job_title = job_title[:100]
            required_skills = str(required_skills)[:500]
            
            result: CVImprovementOutput = await self.improvement_chain.ainvoke({
                "cv_text": cv_text,
                "job_title": job_title,
                "required_skills": required_skills
            })
            
            return result
            
        except Exception as e:
            logger.error(f"CV improvement error: {e}")
            raise
    
    async def explain_job(
        self,
        job_title: str,
        company: str = "Unknown",
        job_description: str = "N/A",
        required_skills: str = "N/A",
        experience_years: int = 3
    ) -> JobExplanationOutput:
        """Explication offre sans tracking état"""
        try:
            job_title = job_title[:100]
            company = company[:100]
            required_skills = str(required_skills)[:500]
            experience_years = max(0, min(50, experience_years))
            
            result: JobExplanationOutput = await self.explanation_chain.ainvoke({
                "job_title": job_title,
                "company": company,
                "job_description": job_description[:2000],
                "required_skills": required_skills,
                "experience_years": experience_years
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Job explanation error: {e}")
            raise
