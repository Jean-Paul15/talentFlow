# Client JSearch API (RapidAPI)
# Gratuit : 200 requetes/mois (BASIC plan, sans carte bancaire)
# Couvre : Google for Jobs -> LinkedIn, Indeed, Glassdoor, ZipRecruiter
# Documentation : https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger


class JSearchClient:
    """
    Client pour JSearch API via RapidAPI.
    Collecte des offres depuis Google for Jobs (agrege LinkedIn, Indeed, etc.)

    Configuration via .env :
        JSEARCH_API_KEY : Cle API RapidAPI (obligatoire)
    """

    BASE_URL = "https://jsearch.p.rapidapi.com"
    HOST = "jsearch.p.rapidapi.com"

    def __init__(self):
        self.api_key = os.getenv("JSEARCH_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("JSearch API desactivee (JSEARCH_API_KEY absent du .env)")

    def _headers(self) -> dict:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.HOST,
        }

    def search_jobs(
        self,
        query: str,
        location: str = "",
        num_pages: int = 1,
        date_posted: str = "week",
    ) -> List[Dict]:
        """
        Recherche des offres d'emploi.

        Args:
            query: Mots-cles (ex: "developer", "comptable", "marketing")
            location: Localisation optionnelle (vide = sans filtre pays)
            num_pages: Nombre de pages (1 page = ~10 jobs)
            date_posted: Filtre date ("all", "today", "3days", "week", "month")

        Returns:
            Liste d'offres normalisees au format JobItem
        """
        if not self.enabled:
            return []

        query_text = f"{query} in {location}" if location.strip() else query
        params = {
            "query": query_text,
            "page": "1",
            "num_pages": str(num_pages),
            "date_posted": date_posted,
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{self.BASE_URL}/search",
                    headers=self._headers(),
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "OK":
                logger.error(f"JSearch erreur: {data.get('error', {})}")
                return []

            jobs = []
            for raw in data.get("data", []):
                normalized = self._normalize(raw)
                if normalized:
                    jobs.append(normalized)

            scope = location if location.strip() else "global"
            logger.info(
                f"JSearch: {len(jobs)} offres pour '{query}' (scope={scope})"
            )
            return jobs

        except httpx.HTTPStatusError as err:
            if err.response.status_code == 429:
                logger.warning("JSearch: limite de requetes atteinte (429)")
            else:
                logger.error(f"JSearch HTTP {err.response.status_code}: {err}")
            return []
        except Exception as err:
            logger.error(f"JSearch erreur: {err}")
            return []

    def _normalize(self, raw: Dict) -> Optional[Dict]:
        """Convertit le format JSearch en format JobItem talentFlow."""
        title = raw.get("job_title", "")
        if not title:
            return None

        # Localisation
        city = raw.get("job_city", "")
        country = raw.get("job_country", "")
        location = f"{city}, {country}" if city else country

        # Salaire
        salary = self._format_salary(raw)

        return {
            "title": title,
            "company": raw.get("employer_name", "Non precise"),
            "location": location or "Non precise",
            "description": raw.get("job_description", ""),
            "source_url": raw.get("job_apply_link", ""),
            "source_name": "jsearch_api",
            "country": country or "Non precise",
            "sector": raw.get("job_job_title", ""),
            "contract_type": raw.get("job_employment_type", ""),
            "salary": salary,
            "skills": [],
            "posted_date": raw.get("job_posted_at_datetime_utc", ""),
            "apply_url": raw.get("job_apply_link", ""),
            "contact_email": None,
            "contact_phone": None,
            "experience": raw.get("job_required_experience", {}).get(
                "required_experience_in_months"
            ),
            "education": raw.get("job_required_education", {}).get(
                "required_education"
            ),
            "deadline": raw.get("job_offer_expiration_datetime_utc"),
            "recruiter_name": raw.get("employer_name"),
            "extra_data": {
                "api_source": "jsearch",
                "job_id": raw.get("job_id"),
                "is_remote": raw.get("job_is_remote"),
                "employer_logo": raw.get("employer_logo"),
                "employer_website": raw.get("employer_website"),
                "publisher": raw.get("job_publisher"),
            },
        }

    def _format_salary(self, raw: Dict) -> str:
        """Formate le salaire si disponible."""
        sal_min = raw.get("job_min_salary")
        sal_max = raw.get("job_max_salary")
        currency = raw.get("job_salary_currency", "")
        period = raw.get("job_salary_period", "")

        if sal_min and sal_max:
            return f"{sal_min} - {sal_max} {currency}/{period}".strip()
        if sal_min:
            return f"{sal_min}+ {currency}/{period}".strip()
        return ""
