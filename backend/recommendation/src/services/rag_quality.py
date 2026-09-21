"""
Calcul de qualité de recherche pour RAG.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def calculate_search_quality(
    query: str,
    matched_jobs: List[Dict[str, Any]],
    cv_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Calcule des métriques de qualité de recherche."""
    try:
        total_jobs = len(matched_jobs)
        if total_jobs == 0:
            return {
                "total_matches": 0,
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "recommendation": "Élargissez vos critères de recherche"
            }
        relevance_scores = [
            job.get('score', 0.5) for job in matched_jobs
        ]
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        unique_companies = len(set(
            job.get('company_name', '') for job in matched_jobs
        ))
        diversity_score = unique_companies / total_jobs if total_jobs > 0 else 0
        recommendation = _generate_quality_recommendation(
            total_jobs, avg_relevance, diversity_score
        )
        return {
            "total_matches": total_jobs,
            "relevance_score": round(avg_relevance, 2),
            "diversity_score": round(diversity_score, 2),
            "recommendation": recommendation
        }
    except Exception as e:
        logger.error(f"Erreur calcul qualité recherche: {e}")
        return {
            "total_matches": 0,
            "relevance_score": 0.0,
            "diversity_score": 0.0,
            "recommendation": "Erreur lors de l'analyse"
        }


def _generate_quality_recommendation(
    total_jobs: int,
    avg_relevance: float,
    diversity_score: float
) -> str:
    """Génère une recommandation basée sur les métriques."""
    if total_jobs < 5:
        return "Peu de résultats - élargissez vos critères"
    elif avg_relevance < 0.5:
        return "Pertinence faible - affinez votre recherche"
    elif diversity_score < 0.3:
        return "Peu de diversité - explorez d'autres entreprises"
    else:
        return "Bonne qualité de recherche - continuez ainsi"
