"""
Requêtes DB pour Enhanced RAG.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def get_market_stats(
    db_pool,
    job_title: str,
    skills: List[str]
) -> Optional[Dict]:
    """Récupère statistiques marché depuis DB."""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_jobs,
                    AVG(salary) as avg_salary,
                    COUNT(DISTINCT company) as companies
                FROM jobs
                WHERE title ILIKE $1
                AND posted_date > NOW() - INTERVAL '90 days'
                """,
                f"%{job_title}%"
            )
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Erreur stats marché: {e}")
        return None


async def get_salary_stats(
    db_pool,
    job_title: str,
    location: str,
    years_experience: int
) -> Optional[Dict]:
    """Récupère statistiques salariales depuis DB."""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT
                    MIN(salary) as min,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) as median,
                    MAX(salary) as max
                FROM jobs
                WHERE title ILIKE $1
                AND location ILIKE $2
                AND required_experience <= $3
                AND salary IS NOT NULL
                """,
                f"%{job_title}%",
                f"%{location}%",
                years_experience + 2
            )
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Erreur stats salaire: {e}")
        return None
