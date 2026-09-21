"""
Service principal de matching (core).
"""
import logging
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer

from ..ml.ranker import MLRankingService
from ..ml.config import RankingConfig
from ..ml.data_collector_core import UserInteractionCollector
from .matching_pipeline import run_matching
from .matching_user_tracking import track_user_interaction

logger = logging.getLogger(__name__)


class JobMatchingService:
    """Matching sémantique CV vs jobs avec ML ranking."""
    
    def __init__(
        self,
        embeddings: SentenceTransformer,
        es_client,
        db_pool: Optional[Any] = None,
        use_ml_ranking: bool = True
    ):
        self.embeddings = embeddings
        self.es = es_client
        self.ranking_config = RankingConfig()
        self.ml_ranker = MLRankingService(self.ranking_config) if use_ml_ranking else None
        self.data_collector = UserInteractionCollector(db_pool) if db_pool else None
        logger.info(
            "JobMatchingService initialisé - ML Ranking: %s, Modèle entraîné: %s",
            use_ml_ranking,
            self.ml_ranker.is_trained if self.ml_ranker else False
        )
    
    async def match_jobs(
        self,
        cv_text: str,
        cv_profile: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Match jobs avec ML ranking intelligent."""
        cv_embedding = self.embeddings.encode(
            cv_text[:2000], convert_to_numpy=True
        )
        return await run_matching(
            es_client=self.es,
            ml_ranker=self.ml_ranker,
            data_collector=self.data_collector,
            cv_embedding=cv_embedding.tolist(),
            cv_profile=cv_profile,
            user_id=user_id,
            session_id=session_id
        )
    
    async def track_user_interaction(
        self,
        user_id: str,
        job_id: str,
        cv_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track interaction utilisateur pour retraining ML."""
        return await track_user_interaction(
            self.data_collector,
            user_id,
            job_id,
            interaction_type,
            metadata
        )
