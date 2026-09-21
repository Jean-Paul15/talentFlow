# Service API Nettoyage pour le dashboard

from typing import Any, Dict

import requests
from loguru import logger

from config import DATA_CLEANING_URL


def lancer_nettoyage(since_hours: int = 24) -> Dict[str, Any]:
    """Appelle l'API data-cleaning pour lancer le nettoyage."""
    try:
        resp = requests.post(
            f"{DATA_CLEANING_URL}/api/clean",
            json={"since_hours": since_hours, "full": False},
            timeout=60,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def statut_nettoyage() -> Dict[str, Any]:
    """Interroge le statut du service de nettoyage."""
    try:
        resp = requests.get(f"{DATA_CLEANING_URL}/api/status", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "indisponible"}


def list_cleaned_jobs(
    *,
    limit: int = 50,
    skip: int = 0,
    source: str | None = None,
    query: str | None = None,
    country: str | None = None,
    stale: bool | None = None,
    expired: bool | None = None,
    min_quality: float | None = None,
) -> Dict[str, Any]:
    """Lit les offres nettoyées depuis data-cleaning (/api/jobs)."""
    params: Dict[str, Any] = {"limit": limit, "skip": skip}
    if source:
        params["source"] = source
    if query:
        params["q"] = query
    if country:
        params["country"] = country
    if stale is not None:
        params["stale"] = str(bool(stale)).lower()
    if expired is not None:
        params["expired"] = str(bool(expired)).lower()
    if min_quality is not None:
        params["min_quality"] = float(min_quality)

    try:
        resp = requests.get(
            f"{DATA_CLEANING_URL}/api/jobs",
            params=params,
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}", "items": []}
    except Exception as err:
        return {"status": "erreur", "detail": str(err), "items": []}
