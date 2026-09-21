"""
Tracking des interactions utilisateur.
"""
import logging
from typing import Dict, Any, Optional

from ..ml.interaction_types import InteractionType
from ..ml.data_collector_core import UserInteractionCollector

logger = logging.getLogger(__name__)


async def track_user_interaction(
    collector: Optional[UserInteractionCollector],
    user_id: str,
    job_id: str,
    interaction_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Track interaction utilisateur pour retraining ML."""
    if not collector:
        logger.warning("Data collector non disponible")
        return False
    try:
        interaction = InteractionType(interaction_type)
        return await collector.track_interaction(
            user_id=user_id,
            job_id=job_id,
            interaction_type=interaction,
            metadata=metadata
        )
    except Exception as e:
        logger.error(f"Erreur tracking interaction: {e}")
        return False
