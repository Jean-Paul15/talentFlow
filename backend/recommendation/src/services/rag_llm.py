"""
Interactions LLM pour Enhanced RAG.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from .rag_schemas import ProfileAnalysis, MarketInsights, SalaryBenchmark
from .rag_prompts import (
    build_profile_analysis_prompt,
    build_market_insights_prompt,
    build_salary_estimate_prompt
)

logger = logging.getLogger(__name__)


async def llm_analyze_profile(
    llm,
    cv_text: str,
    cv_profile: Dict[str, Any]
) -> ProfileAnalysis:
    """Génère analyse profil via LLM."""
    try:
        prompt = build_profile_analysis_prompt(cv_text, cv_profile)
        response = await llm.ainvoke(prompt)
        analysis_data = json.loads(response.content)
        return ProfileAnalysis(**analysis_data)
    except Exception as e:
        logger.error(f"Erreur analyse profil LLM: {e}")
        return _fallback_profile_analysis(cv_profile)


async def llm_market_insights(
    llm,
    job_title: str,
    skills: List[str],
    stats: Optional[Dict] = None
) -> MarketInsights:
    """Génère insights marché via LLM."""
    try:
        prompt = build_market_insights_prompt(job_title, skills, stats)
        response = await llm.ainvoke(prompt)
        insights_data = json.loads(response.content)
        return MarketInsights(**insights_data)
    except Exception as e:
        logger.error(f"Erreur insights marché LLM: {e}")
        return _fallback_market_insights(skills)


async def llm_salary_estimate(
    llm,
    job_title: str,
    location: str,
    years_experience: int
) -> SalaryBenchmark:
    """Estime salaires via LLM."""
    try:
        prompt = build_salary_estimate_prompt(job_title, location, years_experience)
        response = await llm.ainvoke(prompt)
        salary_data = json.loads(response.content)
        return SalaryBenchmark(**salary_data, currency="EUR")
    except Exception as e:
        logger.error(f"Erreur estimation salaire LLM: {e}")
        return _fallback_salary_estimate(years_experience)


def _fallback_profile_analysis(cv_profile: Dict) -> ProfileAnalysis:
    """Analyse profil sans LLM."""
    years = cv_profile.get('years_experience', 0)
    level = "Junior" if years < 2 else ("Mid" if years < 5 else "Senior")
    return ProfileAnalysis(
        strengths=["Expérience solide", "Compétences variées"],
        weaknesses=["À déterminer selon offres"],
        experience_level=level,
        technical_depth="Intermediate",
        soft_skills_assessment="Bon potentiel"
    )


def _fallback_market_insights(skills: List[str]) -> MarketInsights:
    """Insights marché sans LLM."""
    return MarketInsights(
        demand_trend="Forte",
        growth_rate="+15% YoY",
        hot_skills=skills[:3],
        emerging_technologies=["AI/ML", "Cloud Native"],
        market_saturation="Moyenne"
    )


def _fallback_salary_estimate(years_experience: int) -> SalaryBenchmark:
    """Estimation salaire sans LLM."""
    base = 35000 + (years_experience * 3000)
    return SalaryBenchmark(
        min_salary=base * 0.8,
        median_salary=base,
        max_salary=base * 1.4,
        currency="EUR",
        percentile_position=50
    )
