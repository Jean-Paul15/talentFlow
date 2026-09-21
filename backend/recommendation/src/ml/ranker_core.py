"""
Service de ranking ML (core) avec LightGBM.
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from .config import RankingConfig
from .ranker_model import load_model, predict_scores
from .ranker_features import extract_features
from .ranker_scoring import (
    rule_based_scoring,
    apply_diversity_and_freshness,
    select_final_recommendations
)

logger = logging.getLogger(__name__)


class MLRankingService:
    """Service de ranking ML adaptatif avec fallback rule-based."""
    
    def __init__(self, config: Optional[RankingConfig] = None):
        self.config = config or RankingConfig()
        self.model, self.scaler = load_model(self.config)
        self.feature_names = [
            'skills_overlap_ratio',
            'experience_match',
            'semantic_similarity',
            'location_match',
            'user_history_score',
            'salary_ratio',
            'days_since_posted',
            'company_rating',
            'education_match',
            'contract_type_match'
        ]
    
    @property
    def is_trained(self) -> bool:
        return self.model is not None and self.scaler is not None
    
    def calculate_dynamic_pool_size(self, total_jobs: int) -> int:
        """Calcule la taille du pool de candidats (top_k)."""
        pool_size = int(total_jobs * self.config.thresholds.topk_ratio)
        pool_size = max(self.config.thresholds.topk_min, pool_size)
        pool_size = min(self.config.thresholds.topk_max, pool_size)
        return pool_size
    
    def rank(
        self,
        candidates: List[Dict[str, Any]],
        cv_data: Dict[str, Any],
        total_offers_in_db: int,
        user_history: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """Rank les candidats avec modèle ML ou fallback.
        Retourne une liste d'offres enrichies (ml_score, ranking_method).
        """
        if not candidates:
            return []
        top_k = self.calculate_dynamic_pool_size(total_offers_in_db)
        candidates = candidates[:top_k]
        features_list = [
            extract_features(cv_data, job, user_history)
            for job in candidates
        ]
        features_array = np.array([
            [feat[name] for name in self.feature_names]
            for feat in features_list
        ])
        if self.is_trained:
            try:
                scores = predict_scores(self.model, self.scaler, features_array)
                method = "ml_model"
            except Exception as e:
                logger.error(f"Erreur prediction ML: {e}")
                scores = rule_based_scoring(features_array)
                method = "heuristic"
        else:
            scores = rule_based_scoring(features_array)
            method = "heuristic"
        adjusted_scores = apply_diversity_and_freshness(
            candidates, scores, self.config
        )
        ranked_jobs = sorted(
            zip(candidates, adjusted_scores),
            key=lambda x: x[1],
            reverse=True
        )
        final_jobs = select_final_recommendations(ranked_jobs, self.config)
        for job, score in ranked_jobs:
            job['ml_score'] = float(score)
            job['ranking_method'] = method
        return final_jobs
