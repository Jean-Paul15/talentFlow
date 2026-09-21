import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class JoinDataClient:
    """
    Client JoinData.
    Note: la source peut etre indisponible selon la resolution DNS/API.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "JOINDATA_API_URL",
            "https://api.joindata.io/api/v1/jobs/search",
        )

    def search_jobs(self, keyword: str = "python", limit: int = 30) -> List[Dict]:
        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(
                    self.base_url,
                    params={"q": keyword, "limit": limit},
                    headers={"User-Agent": "TalentFlow/1.0"},
                )
                response.raise_for_status()
                payload = response.json()

            rows = payload.get("jobs", []) if isinstance(payload, dict) else []
            jobs: List[Dict] = []
            for raw in rows:
                normalized = self._normalize(raw)
                if normalized:
                    jobs.append(normalized)
            logger.info(f"JoinData: {len(jobs)} offres")
            return jobs
        except Exception as err:
            logger.warning(f"JoinData indisponible: {err}")
            return []

    def _normalize(self, raw: Dict) -> Optional[Dict]:
        title = raw.get("title")
        if not title:
            return None

        return {
            "title": title,
            "company": raw.get("company", "Non precise"),
            "location": raw.get("location", "Non precise"),
            "description": raw.get("description", ""),
            "source_url": raw.get("url", ""),
            "source_name": "joindata_api",
            "country": raw.get("country", "International"),
            "sector": raw.get("category", ""),
            "contract_type": raw.get("type", ""),
            "salary": raw.get("salary", ""),
            "skills": raw.get("skills", []) if isinstance(raw.get("skills"), list) else [],
            "posted_date": raw.get("published_at", datetime.utcnow().isoformat()),
            "apply_url": raw.get("apply_url") or raw.get("url", ""),
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": raw.get("company", "Non precise"),
            "extra_data": {
                "api_source": "joindata",
            },
        }
