"""Status helpers for assistant fallback reporting."""

from __future__ import annotations

__all__ = ["_llm_status_from_error"]


def _llm_status_from_error(llm_error: str | None) -> str:
    lowered = str(llm_error or "").lower()
    if "queue_timeout" in lowered or "queue_overflow" in lowered:
        return "queue_timeout_fallback"
    if "rpm" in lowered or "rate" in lowered:
        return "rate_limited_fallback"
    if any(token in lowered for token in ("gemini unavailable", "timeout", "connection", "api key", "provider")):
        return "provider_error"
    return "fallback_used"
