from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from typing import Any, Optional


_GENERIC_BAD_TITLES = {
    "t",
    "p4",
    "(f/h).",
    "(f/h)",
    "f/h",
    "h/f",
    "poste :",
    "poste:",
    "poste",
    "intitule du poste",
    "intitulé du poste",
    "activites principales",
    "activités principales",
}

_FAST_FEED_SOURCES = {
    "jsearch_global",
    "adzuna",
    "adzuna_za",
    "remoteok",
    "remoteok_api",
    "remotive",
    "remotive_api",
    "hackernews_hiring",
    "hackernews_api",
    "arbeitnow",
    "arbeitnow_api",
    "monster",
}


def annotate_quality_and_freshness(job: dict, *, now: Optional[datetime] = None) -> dict:
    enriched = dict(job or {})
    now_utc = now or datetime.now(timezone.utc)

    freshness_source, freshness_dt = _pick_freshness_source(enriched)
    freshness_days = None
    if freshness_dt is not None:
        freshness_days = max(0, (now_utc.date() - freshness_dt.date()).days)

    expired = _coerce_bool(enriched.get("is_expired"))
    deadline_dt = _parse_dateish(enriched.get("deadline_iso") or enriched.get("deadline"))
    if expired is None and deadline_dt is not None:
        expired = deadline_dt.date() < now_utc.date()
    expired = bool(expired) if expired is not None else False

    ttl_days = _infer_stale_ttl_days(enriched)
    is_stale = False
    stale_reason = None
    if not expired and freshness_days is not None and freshness_days > ttl_days:
        is_stale = True
        stale_reason = f"ttl_exceeded:{freshness_days}>{ttl_days}"
    elif expired:
        stale_reason = "expired"
    elif freshness_source is None:
        stale_reason = "missing_freshness_signal"

    title_conf = _title_confidence(enriched.get("title"))
    location_conf = _location_confidence(enriched.get("location"))
    date_conf = _date_confidence(
        posted_date_iso=enriched.get("posted_date_iso"),
        deadline_iso=enriched.get("deadline_iso"),
        scraped_at=enriched.get("scraped_at"),
    )
    apply_conf = _apply_confidence(
        apply_url=enriched.get("apply_url"),
        apply_email=enriched.get("apply_email") or enriched.get("contact_email"),
        apply_instructions=enriched.get("apply_instructions"),
    )
    desc_conf = _description_confidence(enriched.get("description"))

    quality_score = (
        0.25 * title_conf
        + 0.20 * location_conf
        + 0.20 * date_conf
        + 0.20 * apply_conf
        + 0.15 * desc_conf
    )
    quality_score = max(0.0, min(1.0, round(quality_score, 4)))

    enriched["freshness_source"] = freshness_source
    enriched["freshness_days"] = freshness_days
    enriched["is_expired"] = expired
    enriched["is_stale"] = is_stale
    enriched["stale_reason"] = stale_reason
    enriched["freshness_ttl_days"] = ttl_days
    enriched["title_confidence"] = round(title_conf, 4)
    enriched["location_confidence"] = round(location_conf, 4)
    enriched["date_confidence"] = round(date_conf, 4)
    enriched["apply_confidence"] = round(apply_conf, 4)
    enriched["description_confidence"] = round(desc_conf, 4)
    enriched["quality_score"] = quality_score
    return enriched


def _pick_freshness_source(job: dict) -> tuple[Optional[str], Optional[datetime]]:
    posted_dt = _parse_dateish(job.get("posted_date_iso") or job.get("posted_date"))
    if posted_dt is not None:
        return "posted_date_iso", posted_dt

    scraped_dt = _parse_dateish(job.get("scraped_at"))
    if scraped_dt is not None:
        return "scraped_at", scraped_dt

    deadline_dt = _parse_dateish(job.get("deadline_iso") or job.get("deadline"))
    if deadline_dt is not None:
        return "deadline_iso", deadline_dt
    return None, None


def _infer_stale_ttl_days(job: dict) -> int:
    fast_feed_ttl = _safe_int(os.getenv("FAST_FEED_STALE_TTL_DAYS"), 21)
    api_ttl = _safe_int(os.getenv("API_REMOTE_STALE_TTL_DAYS"), 30)
    local_ttl = _safe_int(os.getenv("LOCAL_BOARD_STALE_TTL_DAYS"), 45)

    source_name = _normalize(job.get("source_name"))
    country = _normalize(job.get("country"))
    location = _normalize(job.get("location"))

    if source_name in _FAST_FEED_SOURCES:
        return fast_feed_ttl
    if country in {"international", "global"} or location in {"remote", "international"}:
        return api_ttl
    if country == "togo":
        return local_ttl
    return api_ttl


def _title_confidence(title: Any) -> float:
    value = _normalize(title)
    if not value:
        return 0.0
    if value in _GENERIC_BAD_TITLES:
        return 0.05
    compact = re.sub(r"[^a-z0-9]+", "", value)
    if len(compact) < 4:
        return 0.1
    length = len(value)
    if length < 8:
        return 0.45
    if length > 180:
        return 0.55
    if "vacance de poste" in value or "vacances de poste" in value:
        return 0.2
    return 0.95


def _location_confidence(location: Any) -> float:
    value = _normalize(location)
    if not value:
        return 0.0
    if value in {"remote", "international"}:
        return 0.75
    if len(value) > 80:
        return 0.2
    if any(tok in value for tok in ("salaire", "experience", "expérience", "indemnit")):
        return 0.15
    return 0.9


def _date_confidence(*, posted_date_iso: Any, deadline_iso: Any, scraped_at: Any) -> float:
    if _parse_dateish(posted_date_iso) and _parse_dateish(deadline_iso):
        return 1.0
    if _parse_dateish(posted_date_iso) or _parse_dateish(deadline_iso):
        return 0.85
    if _parse_dateish(scraped_at):
        return 0.55
    return 0.0


def _apply_confidence(*, apply_url: Any, apply_email: Any, apply_instructions: Any) -> float:
    if _normalize(apply_url) or _normalize(apply_email):
        return 1.0
    instructions = _normalize(apply_instructions)
    if len(instructions) >= 30:
        return 0.7
    if instructions:
        return 0.45
    return 0.0


def _description_confidence(description: Any) -> float:
    value = str(description or "").strip()
    if not value:
        return 0.0
    length = len(value)
    if length >= 600:
        return 1.0
    if length >= 250:
        return 0.85
    if length >= 100:
        return 0.65
    if length >= 40:
        return 0.4
    return 0.1


def _parse_dateish(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if match:
        try:
            return datetime.fromisoformat(match.group(1)).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default
