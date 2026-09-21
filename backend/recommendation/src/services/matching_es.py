"""
Adaptateur de récupération de candidats pour le matching.

Historique:
- initialement couplé à Elasticsearch direct

Évolution:
- backend sélectionnable via env:
  - MATCHING_CANDIDATE_BACKEND=elasticsearch (défaut)
  - MATCHING_CANDIDATE_BACKEND=search_api (via backend/search-engine)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _backend() -> str:
    return os.getenv("MATCHING_CANDIDATE_BACKEND", "elasticsearch").strip().lower()


def _search_api_base() -> str:
    return os.getenv("SEARCH_ENGINE_URL", "http://localhost:8003").rstrip("/")


def get_total_jobs_count(es_client) -> int:
    """Récupère le nombre total de jobs depuis ES direct ou search-engine API."""
    if _backend() == "search_api":
        return _get_total_jobs_count_via_search_api()

    try:
        count_result = es_client.count(index="job_embeddings")
        return count_result.get("count", 0)
    except Exception as e:
        logger.error(f"Erreur count jobs (ES direct): {e}")
        return 1000


def search_candidates(
    es_client,
    cv_embedding: List[float],
    pool_size: int
) -> Dict[str, Any]:
    """
    Recherche de candidats:
    - ES direct (legacy)
    - search-engine API by-vector (découplé)
    """
    if _backend() == "search_api":
        return _search_candidates_via_search_api(cv_embedding=cv_embedding, pool_size=pool_size)

    return es_client.search(
        index="job_embeddings",
        knn={
            "field": "embedding",
            "query_vector": cv_embedding,
            "k": pool_size,
            "num_candidates": pool_size * 2
        },
        size=pool_size,
        _source=[
            "title", "company", "location", "salary_min", "salary_max",
            "required_skills", "required_experience_years", "seniority_level",
            "contract_type", "remote_work", "posted_date", "company_reputation",
            "application_rate"
        ]
    )


def parse_es_results(es_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse les résultats en format interne recommendation.

    Supporte:
    - réponse Elasticsearch native
    - réponse `search-engine` API (`/search/by-vector`)
    """
    if not isinstance(es_results, dict):
        return []

    if "hits" in es_results:
        return _parse_from_elasticsearch(es_results)
    if "results" in es_results:
        return _parse_from_search_api(es_results)
    return []


def _parse_from_elasticsearch(es_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    jobs = []
    for hit in es_results.get("hits", {}).get("hits", []):
        job = hit.get("_source", {})
        job["_score"] = hit.get("_score", 0.0)
        job["id"] = hit.get("_id")
        jobs.append(job)
    return jobs


def _parse_from_search_api(search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for row in search_results.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        jobs.append(
            {
                "id": row.get("id"),
                "_score": float(row.get("score") or 0.0),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "salary_min": row.get("salary_min"),
                "salary_max": row.get("salary_max"),
                "salary": row.get("salary_min") or row.get("salary_max"),
                "required_skills": row.get("required_skills") or row.get("hard_skills") or [],
                # Some feature extractors expect alternate keys.
                "skills_required": row.get("required_skills") or row.get("hard_skills") or [],
                "required_experience_years": row.get("required_experience_years") or row.get("experience_years"),
                "required_experience": row.get("required_experience_years") or row.get("experience_years") or 0,
                "experience_required": row.get("required_experience_years") or row.get("experience_years") or 0,
                "seniority_level": row.get("seniority_level"),
                "contract_type": row.get("contract_type"),
                "remote_work": row.get("remote_work"),
                "posted_date": row.get("posted_date"),
                "company_reputation": row.get("company_reputation", 3.0),
                "company_rating": row.get("company_reputation", 3.0),
                "application_rate": row.get("application_rate"),
                "source_url": row.get("source_url"),
                "source_name": row.get("source_name"),
                "description": row.get("description"),
            }
        )
    return jobs


def _get_total_jobs_count_via_search_api() -> int:
    url = f"{_search_api_base()}/health"
    timeout = float(os.getenv("SEARCH_ENGINE_HTTP_TIMEOUT", "15"))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return int(data.get("doc_count", 0) or 0)
    except Exception as err:
        logger.error(f"Erreur count jobs (search_api): {err}")
        return 1000


def _search_candidates_via_search_api(*, cv_embedding: List[float], pool_size: int) -> Dict[str, Any]:
    url = f"{_search_api_base()}/search/by-vector"
    timeout = float(os.getenv("SEARCH_ENGINE_HTTP_TIMEOUT", "30"))
    payload = {
        "query_vector": cv_embedding,
        "limit": int(pool_size),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as err:
        logger.error(f"Erreur search candidates (search_api): {err}")
        return {"results": []}

