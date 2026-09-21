"""
Service RAG enrichi avec insights de marché, conseils carrière et analyse salariale.
Version compatible avec la politique Gemini-only sans dépendance LLM locale.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .rag_profile import analyze_candidate_profile
from .rag_market import generate_market_insights
from .rag_salary import analyze_salary_expectations
from .rag_career import generate_career_advice
from .rag_quality import calculate_search_quality
from .rag_format import format_job_recommendations

logger = logging.getLogger(__name__)


class EnhancedRAGService:
    """Service RAG enrichi pour des recommandations intelligentes et contextuelles."""

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm
        logger.info("EnhancedRAGService initialise (Gemini-only policy)")

    async def generate_enriched_recommendations(
        self,
        cv_profile: Dict[str, Any],
        matched_jobs: List[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            currency = cv_profile.get('currency', 'EUR')
            profile_analysis = analyze_candidate_profile(cv_profile, matched_jobs, self.llm)
            market_insights = generate_market_insights(cv_profile, matched_jobs, market_data, self.llm)
            salary_analysis = analyze_salary_expectations(cv_profile, matched_jobs, currency)
            career_advice = await generate_career_advice(cv_profile, matched_jobs, self.llm)
            search_quality = calculate_search_quality("", matched_jobs, cv_profile)
            result = {
                "recommendations": format_job_recommendations(matched_jobs),
                "analysis": {
                    "profile_strengths": profile_analysis.get('strengths', ''),
                    "profile_gaps": profile_analysis.get('gaps', ''),
                    "market_insights": market_insights,
                    "salary_range": salary_analysis['range'],
                    "salary_position": salary_analysis['position'],
                    "career_advice": career_advice
                },
                "search_quality": search_quality,
                "generated_at": datetime.utcnow().isoformat()
            }
            logger.info(f"Recommandations generees: {len(matched_jobs)} offres")
            return result
        except Exception as e:
            logger.error(f"Erreur generation: {e}", exc_info=True)
            return self._build_fallback_response(matched_jobs, e)

    def _build_fallback_response(self, matched_jobs: List[Dict[str, Any]], error: Exception) -> Dict[str, Any]:
        return {
            "recommendations": format_job_recommendations(matched_jobs),
            "analysis": {
                "profile_strengths": "Analyse non disponible",
                "profile_gaps": "Analyse non disponible",
                "market_insights": "Donnees de marche non disponibles",
                "salary_range": "N/A",
                "salary_position": "N/A",
                "career_advice": "Conseils non disponibles"
            },
            "search_quality": {
                "total_matches": len(matched_jobs),
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "recommendation": "Erreur lors de l'analyse"
            },
            "error": str(error)
        }
