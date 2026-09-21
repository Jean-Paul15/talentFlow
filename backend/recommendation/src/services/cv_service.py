# Etape 4: Logique metier - CV Analysis Service
from __future__ import annotations

import json
import logging
import re
from typing import Any, List

logger = logging.getLogger(__name__)


class CVAnalysisService:
    """Service analyse CV - mode deterministe compatible Gemini-only"""

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def analyze(self, cv_text: str, user_id: str) -> dict:
        try:
            text = (cv_text or "")[:4000]
            skills = _extract_skills(text)
            experience_level = _infer_experience_level(text)
            summary = text[:150].strip() or "CV non exploitable"

            return {
                "user_id": user_id,
                "summary": summary,
                "skills": skills[:10],
                "experience_level": experience_level,
                "recommendations": [
                    "Ajouter 2 realisations chiffre es directement reliees au poste cible.",
                    "Rendre visibles les outils et stacks utilises.",
                    "Structurer clairement experience, competences et resultats.",
                ],
            }
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            raise


class CVCacheManager:
    """Gestion cache Redis pour CVs"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400

    def get_analysis(self, user_id: str) -> dict:
        key = f"cv:analysis:{user_id}"
        cached = self.redis.get(key)
        return json.loads(cached) if cached else None

    def set_analysis(self, user_id: str, data: dict):
        key = f"cv:analysis:{user_id}"
        self.redis.setex(key, self.ttl, json.dumps(data))


def _extract_skills(text: str) -> List[str]:
    candidates = [
        "python",
        "sql",
        "docker",
        "fastapi",
        "java",
        "javascript",
        "react",
        "flutter",
        "power bi",
        "excel",
        "spark",
        "kafka",
    ]
    lower = text.lower()
    return [skill.title() for skill in candidates if skill in lower]


def _infer_experience_level(text: str) -> str:
    lower = text.lower()
    years = [int(value) for value in re.findall(r"(\d+)\s*(?:ans|years?)", lower)]
    max_years = max(years) if years else 0
    if max_years >= 8:
        return "expert"
    if max_years >= 4:
        return "senior"
    if max_years >= 2:
        return "mid"
    return "junior"
