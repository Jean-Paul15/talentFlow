"""Search helpers for CV text recommendation flows."""

from __future__ import annotations

import httpx
import os
from loguru import logger

__all__ = ["_search_engine_use_by_vector", "_search_jobs"]


def _search_engine_use_by_vector() -> bool:
    raw = str(os.getenv("SEARCH_ENGINE_USE_BY_VECTOR", "true")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def _search_jobs(payload: dict, *, query_vector: list[float] | None = None) -> dict:
    base = (os.getenv("SEARCH_ENGINE_URL") or "http://localhost:8003").rstrip("/")
    timeout_s = float(os.getenv("SEARCH_ENGINE_HTTP_TIMEOUT", "120"))
    timeout = httpx.Timeout(timeout_s, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if query_vector and _search_engine_use_by_vector():
            vector_payload = {
                "query_vector": query_vector,
                "limit": int(payload.get("limit") or 20),
                "location": payload.get("location"),
                "contract_type": payload.get("contract_type"),
                "skills": payload.get("skills"),
            }
            vector_payload = {k: v for k, v in vector_payload.items() if v is not None}
            try:
                resp = await client.post(f"{base}/search/by-vector", json=vector_payload)
                resp.raise_for_status()
                return resp.json()
            except Exception as err:
                logger.warning(f"search-engine /search/by-vector indisponible, fallback texte: {err}")
        try:
            resp = await client.post(f"{base}/search/", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as err:
            logger.error(f"Erreur search-engine /search: {err}")
            return {
                "query": payload.get("query", ""),
                "total": 0,
                "results": [],
                "backend": "search-engine-unavailable",
                "error": str(err),
            }
