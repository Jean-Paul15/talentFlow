"""
Collecte et stockage des interactions utilisateurs.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncpg

from .interaction_types import InteractionType
from .engagement_score import calculate_engagement_score

logger = logging.getLogger(__name__)


class UserInteractionCollector:
    """Collecte et stocke les interactions utilisateurs pour training ML."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def track_interaction(
        self,
        user_id: str,
        job_id: str,
        interaction_type: InteractionType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Enregistre une interaction utilisateur."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_interactions (
                        user_id, job_id, interaction_type,
                        metadata, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    job_id,
                    interaction_type.value,
                    metadata or {},
                    datetime.now()
                )
            logger.debug(
                f"Interaction trackée: user={user_id}, job={job_id}, "
                f"type={interaction_type.value}"
            )
            return True
        except Exception as e:
            logger.error(f"Erreur tracking interaction: {e}")
            return False
    
    async def track_read_time(
        self,
        user_id: str,
        job_id: str,
        read_seconds: int
    ) -> bool:
        """Enregistre le temps de lecture (signal d'engagement fort)."""
        metadata = {
            "read_seconds": read_seconds,
            "engagement_score": calculate_engagement_score(read_seconds)
        }
        return await self.track_interaction(
            user_id, job_id, InteractionType.READ, metadata
        )
    
    async def get_user_history(self, user_id: str, limit: int = 100) -> list:
        """Récupère l'historique des interactions d'un utilisateur."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        ui.job_id,
                        ui.interaction_type,
                        ui.metadata,
                        ui.created_at,
                        j.title,
                        j.company,
                        j.required_skills
                    FROM user_interactions ui
                    LEFT JOIN jobs j ON ui.job_id = j.id
                    WHERE ui.user_id = $1
                    ORDER BY ui.created_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit
                )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return []
