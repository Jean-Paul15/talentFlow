# Service API Lake (bronze data) pour le dashboard.

from typing import Any, Dict, List, Optional

import requests

from config import LAKE_API_URL


def lake_health() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{LAKE_API_URL}/health", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "unhealthy"}


def get_lake_stats() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{LAKE_API_URL}/api/bronze/stats", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"bucket": "-", "total_objects": 0, "per_site": {}}


def list_lake_jobs(
    site: Optional[str] = None,
    date_prefix: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"limit": limit}
    if site:
        params["site"] = site
    if date_prefix:
        params["date_prefix"] = date_prefix

    try:
        resp = requests.get(
            f"{LAKE_API_URL}/api/bronze/jobs",
            params=params,
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def search_lake_jobs(
    query: str,
    site: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"q": query, "limit": limit}
    if site:
        params["site"] = site

    try:
        resp = requests.get(
            f"{LAKE_API_URL}/api/bronze/search",
            params=params,
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def list_lake_sources(sample_limit: int = 2) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(
            f"{LAKE_API_URL}/api/bronze/sources",
            params={"sample_limit": sample_limit},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def list_lake_source_examples(site: str, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(
            f"{LAKE_API_URL}/api/bronze/sources/{site}/examples",
            params={"limit": limit},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []
