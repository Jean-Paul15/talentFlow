"""Low-level text helpers used by CV parsing and ranking."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .parsing_constants import TRACKING_QUERY_KEYS

__all__ = [
    "_build_search_query",
    "_fold_text",
    "_canonicalize_url",
    "_summarize_job",
    "_clean_text",
    "_safe_float",
]


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _fold_text(value: str | None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _build_search_query(
    *,
    cv_text: str,
    skills: list[str],
    experience_years: int | None,
    education_level: str | None,
) -> str:
    first_line = _clean_text(cv_text.splitlines()[0] if cv_text.splitlines() else cv_text) or ""
    first_line = re.sub(r"\s+", " ", first_line)[:120]
    tokens = [first_line] if first_line else []
    if skills:
        tokens.extend(skills[:8])
    if experience_years is not None:
        tokens.append(f"{experience_years} ans experience")
    if education_level:
        tokens.append(education_level)
    seen = set()
    uniq = []
    for token in tokens:
        key = str(token).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(str(token).strip())
    return " ".join(uniq)[:500] or cv_text[:200]


def _canonicalize_url(url: str | None) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith(("mailto:", "tel:")):
        return raw
    if raw.startswith("www."):
        raw = f"https://{raw}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        return raw.rstrip("/")
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw.rstrip("/")
    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    if len(path) > 1:
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = (key or "").lower()
        if lowered in TRACKING_QUERY_KEYS or lowered.startswith("utm_"):
            continue
        query_pairs.append((key, value))
    query_pairs.sort(key=lambda item: (item[0], item[1]))
    return urlunparse((scheme, netloc, path, "", urlencode(query_pairs, doseq=True), ""))


def _summarize_job(row: dict) -> str:
    text = _clean_text(row.get("description")) or ""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if len(text) <= 180:
        return text
    short = text[:180]
    if " " in short:
        short = short.rsplit(" ", 1)[0]
    return short + "..."


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None
