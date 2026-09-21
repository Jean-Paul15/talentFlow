"""
Scoring et post-traitement pour le ranking.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
import numpy as np

from .config import RankingConfig


def rule_based_scoring(features_array: np.ndarray) -> np.ndarray:
    """Scoring rule-based en fallback (poids adaptatifs)."""
    weights = np.array([
        0.35,  # skills_overlap_ratio
        0.20,  # experience_match
        0.15,  # semantic_similarity
        0.08,  # location_match
        0.10,  # user_history_score
        0.05,  # salary_ratio
        0.03,  # days_since_posted
        0.02,  # company_rating
        0.01,  # education_match
        0.01   # contract_type_match
    ])
    scores = features_array @ weights
    return scores * 100


def apply_diversity_and_freshness(
    jobs: List[Dict[str, Any]],
    scores: np.ndarray,
    config: RankingConfig
) -> np.ndarray:
    """Applique pénalités de diversité et boost de fraîcheur."""
    adjusted_scores = scores.copy()
    company_counts: Dict[str, int] = {}
    for i, job in enumerate(jobs):
        company = job.get('company')
        if company in company_counts:
            if company_counts[company] >= config.features.company_repeat_limit:
                adjusted_scores[i] *= 0.5
            else:
                adjusted_scores[i] *= config.features.diversity_penalty
        company_counts[company] = company_counts.get(company, 0) + 1
        posted_date = job.get('posted_date')
        if isinstance(posted_date, str):
            posted_date = datetime.fromisoformat(posted_date)
        if posted_date:
            days_old = (datetime.now() - posted_date).days
            if days_old <= config.features.freshness_boost_days:
                adjusted_scores[i] *= 1.2
            elif days_old >= config.features.old_job_penalty_days:
                adjusted_scores[i] *= 0.8
    return adjusted_scores


def calculate_dynamic_threshold(
    all_scores: np.ndarray,
    config: RankingConfig
) -> float:
    """Calcule le seuil minimum de manière adaptative."""
    if len(all_scores) == 0:
        return 0.0
    return float(
        np.percentile(all_scores, config.thresholds.percentile_threshold)
    )


def select_final_recommendations(
    ranked_jobs: List[Tuple[Dict[str, Any], float]],
    config: RankingConfig
) -> List[Dict[str, Any]]:
    """Sélectionne le nombre final de recommandations de manière adaptative."""
    if not ranked_jobs:
        return []
    scores = np.array([score for _, score in ranked_jobs])
    threshold = calculate_dynamic_threshold(scores, config)
    above_threshold = [
        (job, score) for job, score in ranked_jobs if score >= threshold
    ]
    quality_ratio = len(above_threshold) / len(ranked_jobs)
    if quality_ratio >= 0.5:
        target = config.thresholds.max_recommendations
    elif quality_ratio >= 0.2:
        target = config.thresholds.target_recommendations
    else:
        target = config.thresholds.min_recommendations
    final_count = min(target, len(above_threshold))
    final_count = max(config.thresholds.min_recommendations, final_count)
    return [job for job, _ in above_threshold[:final_count]]
