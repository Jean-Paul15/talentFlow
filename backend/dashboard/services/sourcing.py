# Service API Sourcing pour le dashboard

from typing import Any, Dict, List

import requests
from loguru import logger

from config import JOB_SOURCING_URL

# Timeout genereux : les spiders prennent du temps
SCRAPING_TIMEOUT = 600


def lancer_scraping(sites: List[str], full: bool = False) -> Dict[str, Any]:
    """Appelle l'API job-sourcing pour lancer un scraping."""
    try:
        resp = requests.post(
            f"{JOB_SOURCING_URL}/api/scrape",
            json={"sites": sites, "full": full},
            timeout=SCRAPING_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except requests.exceptions.Timeout:
        return {"status": "erreur", "detail": "Timeout - le scraping continue en arriere-plan"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def statut_sourcing() -> Dict[str, Any]:
    """Interroge le statut du service de sourcing."""
    try:
        resp = requests.get(f"{JOB_SOURCING_URL}/api/status", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "indisponible"}
