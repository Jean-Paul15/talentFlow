from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class RemotiveClient:
    """
    Client Remotive (API publique).
    Endpoint: https://remotive.com/api/remote-jobs
    """

    BASE_URL = "https://remotive.com/api/remote-jobs"

    def fetch_jobs(self, limit: int = 100) -> List[Dict]:
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(self.BASE_URL)
                response.raise_for_status()
                payload = response.json()

            rows = payload.get("jobs", []) if isinstance(payload, dict) else []
            jobs: List[Dict] = []
            for raw in rows:
                normalized = self._normalize(raw)
                if normalized:
                    jobs.append(normalized)
                if len(jobs) >= limit:
                    break

            logger.info(f"Remotive: {len(jobs)} offres")
            return jobs
        except Exception as err:
            logger.error(f"Remotive erreur: {err}")
            return []

    def _normalize(self, raw: Dict) -> Optional[Dict]:
        title = raw.get("title")
        if not title:
            return None

        company = raw.get("company_name", "Non precise")
        location = raw.get("candidate_required_location", "Remote")
        url = raw.get("url", "")
        posted = raw.get("publication_date") or datetime.utcnow().isoformat()

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": raw.get("description", ""),
            "source_url": url,
            "source_name": "remotive_api",
            "country": "International",
            "sector": raw.get("category", "Remote"),
            "contract_type": raw.get("job_type", ""),
            "salary": raw.get("salary", ""),
            "skills": [],
            "posted_date": posted,
            "apply_url": raw.get("url", ""),
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": company,
            "extra_data": {
                "api_source": "remotive",
                "id": raw.get("id"),
                "job_type": raw.get("job_type"),
                "category": raw.get("category"),
            },
        }
