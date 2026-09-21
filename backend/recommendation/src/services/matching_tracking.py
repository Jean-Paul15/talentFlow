"""
Tracking des recommandations et interactions utilisateurs.
"""
import logging
from typing import List, Dict, Any, Optional

from ..ml.interaction_types import InteractionType
from ..ml.data_collector_core import UserInteractionCollector

logger = logging.getLogger(__name__)


async def track_recommendations(
    collector: Optional[UserInteractionCollector],
    user_id: str,
    cv_id: str,
    recommendations: List[Dict[str, Any]],
    session_id: Optional[str] = None
) -> None:
    """Enregistre la recommandation initiale pour tracking."""
    if not collector:
        return
    for rec in recommendations:
        await collector.track_interaction(
            user_id=user_id,
            job_id=rec['job_id'],
            interaction_type=InteractionType.VIEW,
            metadata={
                'position': rec['final_rank'] - 1,
                'scores': {
                    'semantic_score': rec['semantic_score'],
                    'ml_score': rec['ml_score']
                },
                'session_id': session_id
            }
        )
    logger.debug(f"Tracking: {len(recommendations)} recommandations pour user={user_id}")
