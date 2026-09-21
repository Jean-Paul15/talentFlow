"""Text and URL normalization helpers for search filtering."""

from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .filters_base import (
    _COURSE_LIKE_TITLE_PATTERNS,
    _GENERIC_BAD_TITLES,
    _JOB_SIGNAL_KEYWORDS,
    _NON_JOB_TITLE_KEYWORDS,
    _NON_JOB_URL_HINTS,
    _TRACKING_QUERY_KEYS,
)


def _normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _to_plain_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    try:
        return list(value)
    except TypeError:
        return []


def _canonicalize_url(url: str) -> str:
    url = _normalize_space(url)
    if not url:
        return ""
    if url.startswith(("mailto:", "tel:")):
        return url
    if url.startswith("www."):
        url = f"https://{url}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return url
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if len(path) > 1:
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = (key or "").lower()
        if key_lower in _TRACKING_QUERY_KEYS or key_lower.startswith("utm_"):
            continue
        query_pairs.append((key, value))
    query_pairs.sort(key=lambda item: (item[0], item[1]))
    return urlunparse((scheme, netloc, path, "", urlencode(query_pairs, doseq=True), ""))


def _is_probable_non_job_result(row: Dict[str, Any]) -> bool:
    title = _normalize_space(row.get("title")).lower()
    url = _normalize_space(row.get("source_url")).lower()
    description = _normalize_space(row.get("description")).lower()
    text_blob = f"{title} {description}"
    has_job_signal = any(token in text_blob for token in _JOB_SIGNAL_KEYWORDS)
    if title in _GENERIC_BAD_TITLES or re.fullmatch(r"p\d+", title):
        return True
    if re.search(r"\bvacances?\s+de[s]?\s+poste[s]?\b", title):
        return True
    if "cliquez ici pour voir les offres" in description:
        return True
    if any(kw in title for kw in _NON_JOB_TITLE_KEYWORDS):
        course_like = any(title.startswith(prefix) for prefix in _COURSE_LIKE_TITLE_PATTERNS) or " formation " in f" {title} "
        if course_like and not has_job_signal:
            return True
        if not has_job_signal and any(kw in title for kw in ("cours", "certification", "webinar", "webinaire")):
            return True
    if any(hint in url for hint in _NON_JOB_URL_HINTS) and not has_job_signal:
        return True
    return False


__all__ = ["_canonicalize_url", "_is_probable_non_job_result", "_normalize_space", "_to_plain_list"]
