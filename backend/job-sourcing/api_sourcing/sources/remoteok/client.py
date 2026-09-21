import re
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class RemoteOkClient:
    """
    Client RemoteOK (API publique sans cle).
    Endpoint: https://remoteok.com/api
    """

    BASE_URL = "https://remoteok.com/api"

    def fetch_jobs(self, limit: int = 100) -> List[Dict]:
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    self.BASE_URL,
                    headers={"User-Agent": "TalentFlow/1.0"},
                )
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, list):
                logger.warning("RemoteOK: format inattendu")
                return []

            jobs: List[Dict] = []
            for raw in payload:
                normalized = self._normalize(raw)
                if normalized:
                    jobs.append(normalized)
                if len(jobs) >= limit:
                    break

            logger.info(f"RemoteOK: {len(jobs)} offres")
            return jobs

        except Exception as err:
            logger.error(f"RemoteOK erreur: {err}")
            return []

    def _normalize(self, raw: Dict) -> Optional[Dict]:
        if not isinstance(raw, dict):
            return None

        title = raw.get("position") or raw.get("title")
        if not title:
            return None

        company = raw.get("company") or "Non precise"
        location = raw.get("location") or "Remote"
        url = raw.get("url") or self._build_fallback_url(raw)
        description = raw.get("description") or ""
        posted = raw.get("date") or datetime.utcnow().isoformat()
        tags = raw.get("tags", []) if isinstance(raw.get("tags"), list) else []

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "source_url": url,
            "source_name": "remoteok_api",
            "country": "International",
            "sector": "Remote",
            "contract_type": "Remote",
            "salary": self._format_salary(raw),
            "skills": tags,
            "posted_date": posted,
            "apply_url": raw.get("apply_url") or url,
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": company,
            "extra_data": {
                "api_source": "remoteok",
                "id": raw.get("id"),
                "logo": raw.get("logo"),
                "company_logo": raw.get("company_logo"),
                "date": raw.get("date"),
            },
        }

    def _build_fallback_url(self, raw: Dict) -> str:
        slug = raw.get("slug")
        if slug:
            return f"https://remoteok.com/remote-jobs/{slug}"

        raw_id = raw.get("id")
        if raw_id:
            slug_title = raw.get("position") or raw.get("title") or "job"
            slug_title = re.sub(r"[^a-zA-Z0-9]+", "-", slug_title).strip("-").lower()
            return f"https://remoteok.com/remote-jobs/{raw_id}-{slug_title}"

        return "https://remoteok.com/"

    def _format_salary(self, raw: Dict) -> str:
        salary = raw.get("salary")
        if salary:
            return str(salary)

        sal_min = raw.get("salary_min")
        sal_max = raw.get("salary_max")
        if sal_min and sal_max:
            return f"{sal_min} - {sal_max}"
        if sal_min:
            return f"{sal_min}+"
        return ""
