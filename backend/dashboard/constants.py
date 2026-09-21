# Constantes partagees du dashboard TalentFlow
# Les sites sont desormais charges dynamiquement depuis le registre API
# Ce fichier ne sert plus que de fallback si l'API est indisponible

from typing import Any, Dict

import requests
from config import JOB_SOURCING_URL


def _load_sites_from_registry() -> Dict[str, Dict[str, Any]]:
    """Charge les sites depuis l'API du registre."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/sites", timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = {}
            for site_id, info in data.get("sites", {}).items():
                result[site_id] = {
                    "label": info["label"],
                    "url": info["url"],
                    "description": f"{info['category']} - priorite {info['priority']}",
                    "pays": info["pays"],
                    "category": info.get("category", ""),
                    "priority": info.get("priority", 0),
                    "source_type": info.get("source", "scraping"),
                    "spider": info.get("spider", ""),
                    "api_provider": info.get("api_provider"),
                    "has_dedicated_folder": bool(info.get("has_dedicated_folder")),
                    "active": bool(info.get("active", True)),
                }
            return result
    except Exception:
        pass
    return None


# Fallback si le service est indisponible
_FALLBACK_SPIDERS = {
    "anpe_togo": {
        "label": "ANPE Togo",
        "url": "https://anpetogo.org/",
        "description": "Site officiel gouvernemental - offres verifiees",
        "pays": "Togo",
        "category": "gouvernemental",
        "priority": 1,
        "source_type": "scraping",
        "spider": "anpe_togo",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": True,
    },
    "emploi_tg": {
        "label": "Emploi.tg",
        "url": "https://www.emploi.tg/",
        "description": "Plateforme AfricaTalents - leader au Togo",
        "pays": "Togo",
        "category": "portail_emploi",
        "priority": 1,
        "source_type": "scraping",
        "spider": "emploi_tg",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": True,
    },
    "emploitogo_com": {
        "label": "EmploiTogo.com",
        "url": "https://emploitogo.com/",
        "description": "Agence de placement et interim",
        "pays": "Togo",
        "category": "portail_emploi",
        "priority": 2,
        "source_type": "scraping",
        "spider": "emploitogo_com",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": True,
    },
    "miabejob": {
        "label": "MiabeJob",
        "url": "https://miabejob.com/",
        "description": "Service RH et recrutement",
        "pays": "Togo",
        "category": "recrutement",
        "priority": 2,
        "source_type": "scraping",
        "spider": "miabejob",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": False,
    },
    "emploitogo_info": {
        "label": "EmploiTogo.info",
        "url": "https://www.emploitogo.info/",
        "description": "Bourses, stages et offres",
        "pays": "Togo",
        "category": "portail_emploi",
        "priority": 3,
        "source_type": "scraping",
        "spider": "emploitogo_info",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": True,
    },
    "wiijob": {
        "label": "Wiijob",
        "url": "https://wiijob.com/",
        "description": "Coaching carriere Afrique francophone",
        "pays": "Afrique",
        "category": "portail_emploi",
        "priority": 3,
        "source_type": "scraping",
        "spider": "wiijob",
        "api_provider": None,
        "has_dedicated_folder": True,
        "active": True,
    },
    "jsearch_global": {
        "label": "JSearch (Global)",
        "url": "https://jsearch.p.rapidapi.com/search",
        "description": "API Google Jobs sans filtre pays",
        "pays": "Global",
        "category": "api",
        "priority": 2,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "jsearch",
        "has_dedicated_folder": True,
        "active": True,
    },
    "adzuna": {
        "label": "Adzuna",
        "url": "https://api.adzuna.com/v1/api/jobs/",
        "description": "API Adzuna",
        "pays": "International",
        "category": "api",
        "priority": 3,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "adzuna",
        "has_dedicated_folder": True,
        "active": True,
    },
    "remoteok": {
        "label": "RemoteOK",
        "url": "https://remoteok.com/api",
        "description": "API publique jobs remote",
        "pays": "International",
        "category": "api",
        "priority": 3,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "remoteok",
        "has_dedicated_folder": True,
        "active": True,
    },
    "hackernews_hiring": {
        "label": "HackerNews Who is Hiring",
        "url": "https://hacker-news.firebaseio.com/v0/",
        "description": "API officielle Hacker News",
        "pays": "International",
        "category": "api",
        "priority": 3,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "hackernews",
        "has_dedicated_folder": True,
        "active": True,
    },
    "remotive": {
        "label": "Remotive",
        "url": "https://remotive.com/api/remote-jobs",
        "description": "API publique jobs remote",
        "pays": "International",
        "category": "api",
        "priority": 3,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "remotive",
        "has_dedicated_folder": True,
        "active": True,
    },
    "arbeitnow": {
        "label": "Arbeitnow",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "description": "API publique jobs internationaux",
        "pays": "International",
        "category": "api",
        "priority": 3,
        "source_type": "api",
        "spider": "api_aggregator",
        "api_provider": "arbeitnow",
        "has_dedicated_folder": True,
        "active": True,
    },
}


def get_spiders_disponibles() -> Dict[str, Dict[str, Any]]:
    """Retourne les sites disponibles (dynamique ou fallback)."""
    result = _load_sites_from_registry()
    if result:
        return result
    return _FALLBACK_SPIDERS


# Compatibilite : variable utilisee par les anciennes pages
SPIDERS_DISPONIBLES = get_spiders_disponibles()
