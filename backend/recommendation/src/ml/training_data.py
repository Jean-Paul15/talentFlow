"""
Collecte des données d'interactions pour le training.
"""
import logging
from datetime import datetime, timedelta
import pandas as pd
import asyncpg

logger = logging.getLogger(__name__)


async def collect_training_data(db_pool: asyncpg.Pool, days_back: int = 90) -> pd.DataFrame:
    """Collecte les données d'interactions pour training."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    ui.user_id,
                    ui.job_id,
                    ui.interaction_type,
                    ui.metadata,
                    ui.created_at,
                    cv.skills as cv_skills,
                    cv.years_experience as cv_experience,
                    cv.location as cv_location,
                    cv.expected_salary as cv_salary,
                    cv.education_level as cv_education,
                    j.required_skills as job_skills,
                    j.required_experience as job_experience,
                    j.location as job_location,
                    j.salary as job_salary,
                    j.required_education as job_education,
                    j.company,
                    j.company_rating,
                    j.posted_date,
                    j.title
                FROM user_interactions ui
                JOIN cv_profiles cv ON ui.user_id = cv.user_id
                JOIN jobs j ON ui.job_id = j.id
                WHERE ui.created_at >= $1
                """,
                cutoff_date
            )
        logger.info(f"Collecté {len(rows)} interactions pour training")
        return pd.DataFrame([dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Erreur collecte données training: {e}")
        return pd.DataFrame()
