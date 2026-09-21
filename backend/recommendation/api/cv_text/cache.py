"""Redis-backed cache helpers for CV text LLM flows."""

from __future__ import annotations

import hashlib
import json
import os
import re
from threading import RLock

from loguru import logger

try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None

from .runtime_config import _env_flag, _provider_order

__all__ = [
    "_llm_cache_enabled",
    "_get_llm_cache_client",
    "_cache_get_json",
    "_cache_set_json",
    "_hash_text",
    "_prompt_template_version",
    "_jobs_signature",
    "_build_reco_llm_cache_key",
    "_build_offer_llm_cache_key",
    "_build_reco_repair_cache_key",
]

def _llm_cache_enabled() -> bool:
    return _env_flag("LLM_CACHE_ENABLED", True)

def _get_llm_cache_client() -> Redis | None:
    if not _llm_cache_enabled() or Redis is None:
        return None

    global _llm_cache_client
    if _llm_cache_client is not None:
        return _llm_cache_client

    with _llm_cache_lock:
        if _llm_cache_client is not None:
            return _llm_cache_client
        try:
            redis_url = str(os.getenv("REDIS_URL", "")).strip()
            if redis_url:
                _llm_cache_client = Redis.from_url(redis_url, decode_responses=True)
            else:
                host = str(os.getenv("REDIS_HOST", "redis")).strip() or "redis"
                port = int(str(os.getenv("REDIS_PORT", "6379")).strip() or "6379")
                db = int(str(os.getenv("REDIS_DB", "0")).strip() or "0")
                _llm_cache_client = Redis(host=host, port=port, db=db, decode_responses=True)
            _llm_cache_client.ping()
            return _llm_cache_client
        except Exception as err:
            logger.warning(f"LLM cache Redis indisponible: {err}")
            _llm_cache_client = None
            return None

def _cache_get_json(key: str) -> dict | None:
    client = _get_llm_cache_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if not raw:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except Exception as err:
        logger.debug(f"LLM cache get ignore ({key}): {err}")
        return None

def _cache_set_json(key: str, payload: dict, ttl_seconds: int) -> None:
    client = _get_llm_cache_client()
    if client is None:
        return
    try:
        client.setex(key, max(60, int(ttl_seconds)), json.dumps(payload, ensure_ascii=False))
    except Exception as err:
        logger.debug(f"LLM cache set ignore ({key}): {err}")

def _hash_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _prompt_template_version() -> str:
    return str(os.getenv("LLM_PROMPT_TEMPLATE_VERSION", "v2")).strip() or "v2"


def _recommendation_policy_version() -> str:
    return str(os.getenv("RECOMMENDATION_POLICY_VERSION", "score_v3")).strip() or "score_v3"

def _jobs_signature(jobs: list[RecommendedJobPreview], *, limit: int = 8) -> str:
    parts = []
    for row in jobs[: max(1, int(limit))]:
        parts.append(
            "|".join(
                [
                    str(row.id or ""),
                    str(row.title or ""),
                    f"{float(row.score or 0.0):.5f}",
                    str(row.source_url or ""),
                ]
            )
        )
    return _hash_text("||".join(parts))

def _build_reco_llm_cache_key(
    *,
    cv_text: str,
    query_used: str,
    request: CVRecommendTextRequest,
    jobs: list[RecommendedJobPreview],
    expected_mode: str,
) -> str:
    material = "|".join(
        [
            _prompt_template_version(),
            _recommendation_policy_version(),
            _hash_text(cv_text),
            _hash_text(query_used),
            str(request.top_k),
            str(request.location or ""),
            str(request.contract_type or ""),
            str(expected_mode or ""),
            ",".join(_provider_order()),
            str(os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
            _jobs_signature(jobs),
        ]
    )
    return f"llm:cv-recommend:{_hash_text(material)}"

def _build_offer_llm_cache_key(
    *,
    cv_text: str,
    request: CVImproveForOfferRequest,
    missing_skills: list[str],
) -> str:
    material = "|".join(
        [
            _hash_text(cv_text),
            _hash_text(request.job_title),
            _hash_text(request.job_summary),
            str(request.job_url or ""),
            _hash_text(",".join(sorted([str(x).lower() for x in missing_skills]))),
        ]
    )
    return f"llm:cv-improve:{_hash_text(material)}"

def _build_reco_repair_cache_key(
    *,
    cv_text: str,
    expected_mode: str,
    jobs: list[RecommendedJobPreview],
) -> str:
    material = "|".join(
        [
            _prompt_template_version(),
            _hash_text(cv_text),
            str(expected_mode),
            ",".join(_provider_order()),
            _jobs_signature(jobs),
        ]
    )
    return f"llm:cv-recommend:repair:{_hash_text(material)}"

_llm_cache_client = None

_llm_cache_lock = RLock()
