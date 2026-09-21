# Service Search Engine (backend/search-engine) pour le dashboard.

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from config import SEARCH_ENGINE_URL


def search_engine_health() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{SEARCH_ENGINE_URL}/health", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "unhealthy", "search_backend": "unknown"}


def search_jobs_api(
    query: str,
    *,
    limit: int = 10,
    rerank: Optional[bool] = None,
    candidate_pool_size: Optional[int] = None,
    rerank_top_k: Optional[int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"query": query, "limit": int(limit)}
    if rerank is not None:
        payload["rerank"] = bool(rerank)
    if candidate_pool_size is not None:
        payload["candidate_pool_size"] = int(candidate_pool_size)
    if rerank_top_k is not None:
        payload["rerank_top_k"] = int(rerank_top_k)
    try:
        resp = requests.post(f"{SEARCH_ENGINE_URL}/search", json=payload, timeout=45)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"query": query, "total": 0, "results": [], "backend": "unknown"}


def compare_rerank_api(
    query: str,
    *,
    limit: int = 10,
    candidate_pool_size: int = 30,
    rerank_top_k: int = 20,
) -> Dict[str, Any]:
    payload = {
        "query": query,
        "limit": int(limit),
        "candidate_pool_size": int(candidate_pool_size),
        "rerank_top_k": int(rerank_top_k),
    }
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/compare-rerank",
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {
        "query": query,
        "backend": "unknown",
        "baseline_total": 0,
        "reranked_total": 0,
        "baseline": [],
        "reranked": [],
    }


def compare_modes_api(
    query: str,
    *,
    limit: int = 10,
    candidate_pool_size: int = 30,
    rerank_top_k: int = 20,
) -> Dict[str, Any]:
    payload = {
        "query": query,
        "limit": int(limit),
        "candidate_pool_size": int(candidate_pool_size),
        "rerank_top_k": int(rerank_top_k),
    }
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/compare-modes",
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {
        "query": query,
        "backend": "unknown",
        "dense_total": 0,
        "hybrid_total": 0,
        "hybrid_reranked_total": 0,
        "dense": [],
        "hybrid": [],
        "hybrid_reranked": [],
    }


def evaluate_search_api(
    query: str,
    *,
    relevant_ids: Optional[List[str]] = None,
    graded_relevance: Optional[Dict[str, float]] = None,
    limit: int = 10,
    candidate_pool_size: int = 30,
    rerank_top_k: int = 20,
    k_values: Optional[List[int]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "query": query,
        "limit": int(limit),
        "candidate_pool_size": int(candidate_pool_size),
        "rerank_top_k": int(rerank_top_k),
        "k_values": k_values or [5, 10],
    }
    if relevant_ids:
        payload["relevant_ids"] = relevant_ids
    if graded_relevance:
        payload["graded_relevance"] = graded_relevance
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/evaluate",
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def get_rerank_policy_api(*, history_limit: int = 20) -> Dict[str, Any]:
    try:
        resp = requests.get(
            f"{SEARCH_ENGINE_URL}/search/rerank-policy",
            params={"history_limit": int(history_limit)},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def set_rerank_policy_manual_api(enabled: bool) -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/rerank-policy/manual",
            json={"enabled": bool(enabled)},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def set_rerank_policy_auto_api() -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/rerank-policy/auto",
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def evaluate_search_batch_api(
    cases: List[Dict[str, Any]],
    *,
    limit: int = 10,
    candidate_pool_size: int = 30,
    rerank_top_k: int = 20,
    k_values: Optional[List[int]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "cases": cases,
        "limit": int(limit),
        "candidate_pool_size": int(candidate_pool_size),
        "rerank_top_k": int(rerank_top_k),
        "k_values": k_values or [5, 10],
    }
    try:
        resp = requests.post(
            f"{SEARCH_ENGINE_URL}/search/evaluate-batch",
            json=payload,
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def vector_preview_api(
    *,
    limit: int = 120,
    source_name: Optional[str] = None,
    country: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"limit": int(limit)}
    if source_name:
        params["source_name"] = source_name
    if country:
        params["country"] = country
    try:
        resp = requests.get(
            f"{SEARCH_ENGINE_URL}/search/vector-preview",
            params=params,
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def search_sync_status_api() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{SEARCH_ENGINE_URL}/index/sync-status", timeout=20)
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}
