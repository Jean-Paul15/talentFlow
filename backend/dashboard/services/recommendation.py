from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from config import RECOMMENDATION_URL


def recommendation_health() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{RECOMMENDATION_URL}/health", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {"status": "unhealthy", "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"status": "unhealthy", "detail": str(err)}


def recommendation_llm_runtime() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{RECOMMENDATION_URL}/cv/llm-runtime", timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}


def recommend_from_cv_text_api(
    cv_text: str,
    *,
    file_name: str = "cv.pdf",
    top_k: int = 5,
    location: Optional[str] = None,
    contract_type: Optional[str] = None,
    use_llm: bool = True,
    rerank: Optional[bool] = None,
    candidate_pool_size: Optional[int] = None,
    llm_model: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "cv_text": cv_text,
        "file_name": file_name,
        "top_k": int(top_k),
        "use_llm": bool(use_llm),
    }
    if location:
        payload["location"] = location
    if contract_type:
        payload["contract_type"] = contract_type
    if rerank is not None:
        payload["rerank"] = bool(rerank)
    if candidate_pool_size is not None:
        payload["candidate_pool_size"] = int(candidate_pool_size)
    if llm_model:
        payload["llm_model"] = llm_model

    try:
        resp = requests.post(
            f"{RECOMMENDATION_URL}/cv/recommend-text",
            json=payload,
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": True, "status_code": resp.status_code, "detail": resp.text}
    except Exception as err:
        return {"error": True, "detail": str(err)}
