# Client Adzuna API
# Gratuit : inscription sur developer.adzuna.com
# Couverture internationale, API officielle et stable
# Documentation : https://developer.adzuna.com/

import os
from typing import Dict, List, Optional

import httpx
from loguru import logger


# Codes pays Adzuna disponibles pour l'Afrique / francophonie
ADZUNA_COUNTRIES = {
    "za": "Afrique du Sud",
    "fr": "France",
    "gb": "Royaume-Uni",
    "de": "Allemagne",
    "at": "Autriche",
    "br": "Bresil",
    "in": "Inde",
    "sg": "Singapour",
}

# Pays utilises pour les requetes TalentFlow
TALENTFLOW_SEARCH_COUNTRIES = ["za", "fr"]


class AdzunaClient:
    """
    Client pour Adzuna API officielle.
    Collecte des offres depuis l'agregateur international Adzuna.

    Configuration via .env :
        ADZUNA_APP_ID : ID application (obligatoire)
        ADZUNA_APP_KEY : Cle API (obligatoire)
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self):
        self.app_id = os.getenv("ADZUNA_APP_ID", "")
        self.app_key = os.getenv("ADZUNA_APP_KEY", "")
        self.enabled = bool(self.app_id and self.app_key)
        if not self.enabled:
            logger.warning(
                "Adzuna API desactivee "
                "(ADZUNA_APP_ID / ADZUNA_APP_KEY absents du .env)"
            )

    def search_jobs(
        self,
        what: str = "",
        where: str = "",
        country: str = "fr",
        results_per_page: int = 20,
        page: int = 1,
    ) -> List[Dict]:
        """
        Recherche des offres sur Adzuna.

        Args:
            what: Mots-cles (ex: "developpeur", "marketing")
            where: Localisation (ex: "Paris", "Afrique")
            country: Code pays Adzuna (ex: "fr", "za")
            results_per_page: Nombre de resultats par page (max 50)
            page: Numero de page

        Returns:
            Liste d'offres normalisees au format JobItem
        """
        if not self.enabled:
            return []

        url = f"{self.BASE_URL}/{country}/search/{page}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": min(results_per_page, 50),
        }
        if what:
            params["what"] = what
        if where:
            params["where"] = where

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            jobs = []
            for raw in data.get("results", []):
                normalized = self._normalize(raw, country)
                if normalized:
                    jobs.append(normalized)

            count = data.get("count", 0)
            logger.info(
                f"Adzuna [{country}]: {len(jobs)} offres "
                f"(total disponible: {count}) pour '{what}'"
            )
            return jobs

        except httpx.HTTPStatusError as err:
            logger.error(f"Adzuna HTTP {err.response.status_code}: {err}")
            return []
        except Exception as err:
            logger.error(f"Adzuna erreur: {err}")
            return []

    def search_multi_country(
        self, what: str, countries: List[str] = None
    ) -> List[Dict]:
        """
        Recherche dans plusieurs pays simultanement.

        Args:
            what: Mots-cles de recherche
            countries: Liste de codes pays (defaut: za, fr)

        Returns:
            Liste combinee d'offres de tous les pays
        """
        countries = countries or TALENTFLOW_SEARCH_COUNTRIES
        all_jobs = []

        for country_code in countries:
            jobs = self.search_jobs(what=what, country=country_code)
            all_jobs.extend(jobs)

        return all_jobs

    def _normalize(self, raw: Dict, country_code: str) -> Optional[Dict]:
        """Convertit le format Adzuna en format JobItem talentFlow."""
        title = raw.get("title", "")
        if not title:
            return None

        company = raw.get("company", {})
        company_name = company.get("display_name", "Non precise") if company else "Non precise"
        location = raw.get("location", {})
        area = location.get("display_name", "Non precise") if location else "Non precise"

        # Salaire
        salary = self._format_salary(raw)

        return {
            "title": title,
            "company": company_name,
            "location": area,
            "description": raw.get("description", ""),
            "source_url": raw.get("redirect_url", ""),
            "source_name": "adzuna_api",
            "country": ADZUNA_COUNTRIES.get(country_code, country_code),
            "sector": raw.get("category", {}).get("label", ""),
            "contract_type": raw.get("contract_type", ""),
            "salary": salary,
            "skills": [],
            "posted_date": raw.get("created", ""),
            "apply_url": raw.get("redirect_url", ""),
            "contact_email": None,
            "contact_phone": None,
            "experience": None,
            "education": None,
            "deadline": None,
            "recruiter_name": company_name,
            "extra_data": {
                "api_source": "adzuna",
                "adzuna_id": raw.get("id"),
                "contract_time": raw.get("contract_time"),
                "latitude": raw.get("latitude"),
                "longitude": raw.get("longitude"),
                "category_tag": raw.get("category", {}).get("tag", ""),
            },
        }

    def _format_salary(self, raw: Dict) -> str:
        """Formate le salaire si disponible."""
        sal_min = raw.get("salary_min")
        sal_max = raw.get("salary_max")

        if sal_min and sal_max:
            return f"{sal_min:.0f} - {sal_max:.0f}"
        if sal_min:
            return f"{sal_min:.0f}+"
        return ""
