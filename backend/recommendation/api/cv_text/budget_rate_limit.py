"""Rate-limit helpers for CV text recommendation flows."""

from __future__ import annotations

import os
import time

from fastapi import Request
from loguru import logger

from .cache import _get_llm_cache_client
from .runtime_config import _env_int

__all__ = ["_client_ip", "_rate_guard_allow", "_deepseek_rate_limit_allow"]


def _client_ip(request_obj: Request | None) -> str:
    if request_obj is None:
        return "unknown"
    xff = str(request_obj.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    return str(getattr(getattr(request_obj, "client", None), "host", "") or "unknown").strip() or "unknown"


def _rate_guard_allow(*, scope: str, limit: int, key_suffix: str, window_seconds: int = 60) -> bool:
    if limit <= 0:
        return True
    client = _get_llm_cache_client()
    if client is None:
        return True
    bucket = int(time.time() // max(1, window_seconds))
    key = f"ratelimit:{scope}:{key_suffix}:{bucket}"
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, max(2, window_seconds + 2))
        return count <= limit
    except Exception as err:
        logger.debug(f"Rate guard ignore ({scope}): {err}")
        return True


def _deepseek_rate_limit_allow(client_ip: str) -> tuple[bool, str | None]:
    global_limit = _env_int("DEEPSEEK_RPM_GLOBAL", 120)
    per_ip_limit = _env_int("DEEPSEEK_RPM_PER_IP", 20)
    if not _rate_guard_allow(scope="deepseek:rpm:global", limit=global_limit, key_suffix="all"):
        return False, "deepseek_rpm_global_exceeded"
    if not _rate_guard_allow(scope="deepseek:rpm:ip", limit=per_ip_limit, key_suffix=client_ip):
        return False, "deepseek_rpm_per_ip_exceeded"
    return True, None
