"""Result-level filtering and deduplication helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .filters_text import _canonicalize_url, _is_probable_non_job_result, _normalize_space


def _dedupe_and_filter_results(results: List[Dict[str, Any]], *, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    seen_semantic: set[str] = set()
    seen_semantic_base_same_domain: set[str] = set()
    for row in results or []:
        if not isinstance(row, dict):
            continue
        if row.get("source_url"):
            row["source_url"] = _canonicalize_url(str(row.get("source_url") or ""))
        company = _normalize_space(row.get("company"))
        if len(company) > 140 or company.count(" ") > 18:
            row["company"] = None
        title = _normalize_space(row.get("title"))
        if len(title) > 260:
            row["title"] = title[:260].rsplit(" ", 1)[0]
        if _is_probable_non_job_result(row):
            continue
        canonical_url = _canonicalize_url(str(row.get("source_url") or ""))
        try:
            source_domain = (urlparse(canonical_url).netloc or "").lower().replace("www.", "")
        except Exception:
            source_domain = ""
        semantic_key = "|".join([
            _normalize_space(row.get("title")).lower(),
            _normalize_space(row.get("company")).lower(),
            _normalize_space(row.get("location")).lower(),
            _normalize_space(row.get("posted_date")).lower(),
        ])
        semantic_base_key = "|".join([
            _normalize_space(row.get("title")).lower(),
            _normalize_space(row.get("company")).lower(),
            _normalize_space(row.get("location")).lower(),
        ])
        key = f"url:{canonical_url}" if canonical_url else f"fallback:{semantic_key}"
        if key in seen:
            continue
        if semantic_key and semantic_key != "|||" and semantic_key in seen_semantic:
            continue
        if semantic_base_key and semantic_base_key != "||" and source_domain:
            if f"{source_domain}|{semantic_base_key}" in seen_semantic_base_same_domain:
                continue
        seen.add(key)
        if semantic_key and semantic_key != "|||":
            seen_semantic.add(semantic_key)
        if semantic_base_key and semantic_base_key != "||" and source_domain:
            seen_semantic_base_same_domain.add(f"{source_domain}|{semantic_base_key}")
        out.append(row)
        if max_items and len(out) >= max_items:
            break
    return out


__all__ = ["_dedupe_and_filter_results"]
