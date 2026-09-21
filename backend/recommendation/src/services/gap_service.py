# Etape 4: Gap Analysis Service
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GapAnalysisService:
    """Identifie les gaps de maniere deterministe"""

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def analyze_gaps(self, cv_text: str, job_title: str) -> dict:
        try:
            lower_cv = (cv_text or "").lower()
            title = (job_title or "").strip()

            missing = []
            for keyword, suggestion in (
                ("docker", "Docker"),
                ("sql", "SQL"),
                ("python", "Python"),
                ("kubernetes", "Kubernetes"),
                ("power bi", "Power BI"),
            ):
                if keyword in title.lower() and keyword not in lower_cv:
                    missing.append(suggestion)

            if not missing:
                missing = ["Adapter les experiences au poste cible", "Ajouter des resultats chiffres"]

            return {
                "job_title": title,
                "missing_skills": missing,
                "learning_path": missing[:3],
                "estimated_weeks": max(4, len(missing) * 2),
            }
        except Exception as e:
            logger.error(f"Gap analysis error: {e}")
            raise
