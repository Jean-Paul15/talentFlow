"""Ranking helpers for the search service."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .filters import _env, _env_float

_SEARCH_EXCLUDE_EXPIRED = _env("SEARCH_EXCLUDE_EXPIRED", "true").lower() in {"1", "true", "yes", "on"}
_SEARCH_STALE_PENALTY = max(0.10, min(_env_float("SEARCH_STALE_PENALTY", 0.72), 1.0))
_SEARCH_MIN_QUALITY_USER_FACING = max(0.0, min(_env_float("SEARCH_MIN_QUALITY_USER_FACING", 0.20), 1.0))
_SEARCH_MIN_TITLE_CONFIDENCE = max(0.0, min(_env_float("SEARCH_MIN_TITLE_CONFIDENCE", 0.20), 1.0))
_SEARCH_TEXT_NOISE_PENALTY = max(0.05, min(_env_float("SEARCH_TEXT_NOISE_PENALTY", 0.78), 1.0))

_NOISY_TEXT_MARKERS = (
    "cliquez pour lire",
    "chercheurs d'emploi",
    "chercheurs d emploi",
    "nos conseils en recherche",
    "formation certifiante",
    "inscription chercheurs",
    "platon",
)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _quality_multiplier(row: Dict[str, Any]) -> float:
    quality = _coerce_float(row.get("quality_score"), 0.0)
    return 0.65 + (0.35 * max(0.0, min(quality, 1.0)))


def _text_cleanliness_multiplier(row: Dict[str, Any]) -> float:
    blob = " ".join(
        str(row.get(key) or "").strip().lower()
        for key in ("title", "company", "description", "summary")
    )
    if any(marker in blob for marker in _NOISY_TEXT_MARKERS):
        return _SEARCH_TEXT_NOISE_PENALTY
    compact_company = re.sub(r"\s+", " ", str(row.get("company") or "").strip())
    if len(compact_company) > 90:
        return 0.88
    return 1.0


def _freshness_multiplier(row: Dict[str, Any]) -> float:
    freshness_days = row.get("freshness_days")
    if freshness_days is None:
        return 1.0
    try:
        days = int(freshness_days)
    except Exception:
        return 1.0
    if days <= 7:
        return 1.02
    if days <= 30:
        return 1.0
    if days <= 60:
        return 0.97
    return 0.94


def _tokenize_query(value: str | None) -> list[str]:
    txt = re.sub(r"[^a-z0-9+#./_-]+", " ", str(value or "").lower())
    out: list[str] = []
    for token in txt.split():
        if len(token) < 2:
            continue
        if token in {"de", "du", "des", "la", "le", "les", "et", "or", "ou", "en", "to"}:
            continue
        out.append(token)
    return out


def _intent_multiplier(row: Dict[str, Any], query: str | None) -> float:
    tokens = _tokenize_query(query)
    if not tokens:
        return 1.0
    title = str(row.get("title") or "").lower()
    summary = str(row.get("summary") or row.get("description") or "").lower()
    title_hits = sum(1 for token in tokens if token in title)
    summary_hits = sum(1 for token in tokens if token in summary)
    title_ratio = title_hits / max(1, len(tokens))
    summary_ratio = summary_hits / max(1, len(tokens))

    # Bias relevance toward explicit title/role intent from the query.
    return 0.88 + min(0.28, title_ratio * 0.24 + summary_ratio * 0.12)


def _apply_user_facing_quality_policies(
    results: List[Dict[str, Any]],
    *,
    exclude_expired: bool = _SEARCH_EXCLUDE_EXPIRED,
    query: str | None = None,
) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for row in results or []:
        if not isinstance(row, dict):
            continue
        if exclude_expired and bool(row.get("is_expired")):
            continue
        if _coerce_float(row.get("title_confidence"), 0.0) < _SEARCH_MIN_TITLE_CONFIDENCE:
            continue
        if _coerce_float(row.get("quality_score"), 0.0) < _SEARCH_MIN_QUALITY_USER_FACING:
            continue

        base_score = _coerce_float(row.get("rerank_score") if row.get("rerank_score") is not None else row.get("score"), 0.0)
        adjusted = (
            base_score
            * _quality_multiplier(row)
            * _intent_multiplier(row, query)
            * _freshness_multiplier(row)
            * _text_cleanliness_multiplier(row)
        )
        if bool(row.get("is_stale")):
            adjusted *= _SEARCH_STALE_PENALTY
        row["score"] = round(adjusted, 6)
        scored.append(row)

    scored.sort(
        key=lambda r: (
            _coerce_float(r.get("score"), 0.0),
            _coerce_float(r.get("quality_score"), 0.0),
            _coerce_float(r.get("title_confidence"), 0.0),
            -_coerce_float(r.get("freshness_days"), 9999.0),
        ),
        reverse=True,
    )
    return scored


__all__ = [
    "_apply_user_facing_quality_policies",
    "_coerce_float",
    "_freshness_multiplier",
    "_quality_multiplier",
]
