from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class ArbeitnowClient:
    """
    Client Arbeitnow (API publique).
    Endpoint: https://www.arbeitnow.com/api/job-board-api
    """

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self, limit: int = 100) -> List[Dict]:
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(self.BASE_URL)
                response.raise_for_status()
                payload = response.json()

            rows = payload.get("data", []) if isinstance(payload, dict) else []
            jobs: List[Dict] = []
            for raw in rows:
                normalized = self._normalize(raw)
                if normalized:
                    jobs.append(normalized)
                if len(jobs) >= limit:
                    break

            logger.info(f"Arbeitnow: {len(jobs)} offres")
            return jobs
        except Exception as err:
            logger.error(f"Arbeitnow erreur: {err}")
            return []

    def _normalize(self, raw: Dict) -> Optional[Dict]:
        title = raw.get("title")
        if not title:
            return None

        company = raw.get("company_name", "Non precise")
        location = raw.get("location", "Remote")
        url = raw.get("url", "")
        tags = raw.get("tags", []) if isinstance(raw.get("tags"), list) else []
        remote = raw.get("remote", False)

        posted = raw.get("created_at")
        if isinstance(posted, str) and posted.strip():
            posted_date = posted
        else:
            posted_date = datetime.utcnow().isoformat()

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": raw.get("description", ""),
            "source_url": url,
            "source_name": "arbeitnow_api",
            "country": "International",
            "sector": "Tech",
            "contract_type": "Remote" if remote else "",
            "salary": "",
            "skills": tags,
            "posted_date": posted_date,
            "apply_url": raw.get("url", ""),
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": company,
            "extra_data": {
                "api_source": "arbeitnow",
                "slug": raw.get("slug"),
                "remote": remote,
                "job_types": raw.get("job_types", []),
            },
        }
