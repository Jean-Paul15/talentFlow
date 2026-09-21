"""
Service RAG enrichi - Orchestrateur principal.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from .rag_schemas import (
    ProfileAnalysis,
    MarketInsights,
    SalaryBenchmark,
    CareerAdvice,
    EnhancedRecommendationOutput
)
from .rag_llm import llm_analyze_profile, llm_market_insights, llm_salary_estimate
from .rag_db import get_market_stats, get_salary_stats

logger = logging.getLogger(__name__)


class EnhancedRAGOrchestrator:
    """Orchestrateur RAG enrichi avec analyses complètes."""
    
    def __init__(self, llm, db_pool=None):
        self.llm = llm
        self.db_pool = db_pool
    
    async def generate_profile_analysis(
        self,
        cv_text: str,
        cv_profile: Dict[str, Any]
    ) -> ProfileAnalysis:
        """Délègue à rag_llm."""
        return await llm_analyze_profile(self.llm, cv_text, cv_profile)
    
    async def generate_market_insights(
        self,
        job_title: str,
        skills: List[str]
    ) -> MarketInsights:
        """Délègue à rag_db + rag_llm."""
        stats = None
        if self.db_pool:
            stats = await get_market_stats(self.db_pool, job_title, skills)
        return await llm_market_insights(self.llm, job_title, skills, stats)
    
    async def generate_salary_benchmark(
        self,
        job_title: str,
        location: str,
        years_experience: int
    ) -> SalaryBenchmark:
        """Délègue à rag_db ou rag_llm."""
        if self.db_pool:
            salary_data = await get_salary_stats(
                self.db_pool, job_title, location, years_experience
            )
            if salary_data:
                return SalaryBenchmark(
                    min_salary=salary_data['min'],
                    median_salary=salary_data['median'],
                    max_salary=salary_data['max'],
                    currency="EUR",
                    percentile_position=salary_data.get('percentile', 50)
                )
        return await llm_salary_estimate(self.llm, job_title, location, years_experience)
    
    async def generate_career_advice(
        self,
        cv_profile: Dict[str, Any],
        gap_analysis: Optional[Dict] = None
    ) -> CareerAdvice:
        """Génère conseils carrière personnalisés."""
        try:
            gaps = gap_analysis.get('missing_skills', []) if gap_analysis else []
            prompt = f"""Génère des conseils de carrière personnalisés pour ce profil:

Expérience: {cv_profile.get('years_experience', 0)} ans
Compétences: {cv_profile.get('skills', [])}
Lacunes identifiées: {gaps}

Format JSON:
{{
    "immediate_actions": ["action 1", "action 2", "action 3"],
    "short_term_goals": ["objectif 1", "objectif 2"],
    "certifications_recommended": ["cert 1", "cert 2"],
    "learning_paths": ["parcours 1", "parcours 2"],
    "networking_tips": ["conseil 1", "conseil 2"]
}}"""
            response = await self.llm.ainvoke(prompt)
            advice_data = json.loads(response.content)
            return CareerAdvice(**advice_data)
        except Exception as e:
            logger.error(f"Erreur conseils carrière: {e}")
            return self._fallback_career_advice()
    
    def _fallback_career_advice(self) -> CareerAdvice:
        """Conseils génériques sans LLM."""
        return CareerAdvice(
            immediate_actions=["Mettre à jour CV", "Optimiser LinkedIn", "Projets GitHub"],
            short_term_goals=["Certification pertinente", "Contribuer open-source"],
            certifications_recommended=["AWS", "Kubernetes", "Scrum"],
            learning_paths=["Cloud Computing", "DevOps"],
            networking_tips=["Meetups locaux", "Communautés en ligne"]
        )
