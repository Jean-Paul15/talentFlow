"""
Pipeline de matching pour recommandations.
"""
from typing import Dict, Any, List, Optional

from ..ml.ranker import MLRankingService
from .matching_es import get_total_jobs_count, search_candidates, parse_es_results
from .matching_format import format_final_results
from .matching_tracking import track_recommendations


def build_empty_response(pool_size: int, total_jobs: int) -> Dict[str, Any]:
    """Construit une réponse vide standardisée."""
    return {
        "recommendations": [],
        "metadata": {
            "total_analyzed": 0,
            "returned_count": 0,
            "ranking_method": "none",
            "pool_size": pool_size,
            "total_jobs_in_db": total_jobs
        }
    }


def apply_fallback_ranking(
    candidate_jobs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Fallback: tri simple par score sémantique."""
    ranked = sorted(
        candidate_jobs,
        key=lambda x: x.get('_score', 0),
        reverse=True
    )[:10]
    for job in ranked:
        job['ml_score'] = job.get('_score', 0.0)
        job['ranking_method'] = 'semantic_fallback'
    return ranked


def get_pool_size(total_jobs: int, ml_ranker: Optional[MLRankingService]) -> int:
    """Calcule le pool_size selon configuration ML ou fallback."""
    if ml_ranker:
        return ml_ranker.calculate_dynamic_pool_size(total_jobs)
    return min(100, max(50, int(total_jobs * 0.10)))


def extract_candidates(es_client, cv_embedding: List[float], pool_size: int) -> List[Dict[str, Any]]:
    """Extrait les candidats depuis Elasticsearch."""
    es_results = search_candidates(es_client, cv_embedding, pool_size)
    return parse_es_results(es_results)


def build_metadata(
    candidate_jobs: List[Dict[str, Any]],
    formatted: List[Dict[str, Any]],
    method: str,
    pool_size: int,
    total_jobs: int,
    ml_ranker: Optional[MLRankingService]
) -> Dict[str, Any]:
    """Construit les métadonnées de réponse."""
    return {
        "total_analyzed": len(candidate_jobs),
        "returned_count": len(formatted),
        "ranking_method": method,
        "pool_size": pool_size,
        "total_jobs_in_db": total_jobs,
        "ml_model_trained": ml_ranker.is_trained if ml_ranker else False
    }


async def run_matching(
    es_client,
    ml_ranker: Optional[MLRankingService],
    data_collector,
    cv_embedding: List[float],
    cv_profile: Optional[Dict[str, Any]],
    user_id: Optional[str],
    session_id: Optional[str]
) -> Dict[str, Any]:
    """Exécute le pipeline de matching complet."""
    total_jobs = get_total_jobs_count(es_client)
    pool_size = get_pool_size(total_jobs, ml_ranker)
    candidate_jobs = extract_candidates(es_client, cv_embedding, pool_size)
    if not candidate_jobs:
        return build_empty_response(pool_size, total_jobs)
    if ml_ranker and cv_profile:
        for job in candidate_jobs:
            job['semantic_score'] = job.get('_score', 0.0)
        ranked_jobs = ml_ranker.rank(
            candidates=candidate_jobs,
            cv_data=cv_profile,
            total_offers_in_db=total_jobs
        )
        method = ranked_jobs[0].get('ranking_method', 'ml_model') if ranked_jobs else 'ml_model'
    else:
        ranked_jobs = apply_fallback_ranking(candidate_jobs)
        method = "semantic_fallback"
    formatted = format_final_results(ranked_jobs, method)
    if data_collector and user_id:
        await track_recommendations(
            data_collector,
            user_id,
            cv_profile.get('cv_id', 'unknown') if cv_profile else 'unknown',
            formatted,
            session_id
        )
    return {
        "recommendations": formatted,
        "metadata": build_metadata(
            candidate_jobs, formatted, method, pool_size, total_jobs, ml_ranker
        )
    }
