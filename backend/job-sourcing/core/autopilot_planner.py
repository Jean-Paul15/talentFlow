"""Adaptive sourcing autopilot planner (freshness + reliability aware)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .registry_constants import PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY
from .sites_registry import get_api_sites, get_spider_sites
from .sourcing_reports import read_scrape_reports
from .source_bandit import score_for_target, update_bandit_with_reports


PRIORITY_INTERVAL_MINUTES = {
    PRIORITY_HIGH: 8 * 60,       # ~3x/jour
    PRIORITY_MEDIUM: 12 * 60,    # ~2x/jour
    PRIORITY_LOW: 24 * 60,       # 1x/jour
    PRIORITY_NIGHTLY: 24 * 60,   # 1x/nuit (cadence journaliere)
}

PRIORITY_WEIGHTS = {
    PRIORITY_HIGH: 100.0,
    PRIORITY_MEDIUM: 70.0,
    PRIORITY_LOW: 40.0,
    PRIORITY_NIGHTLY: 20.0,
}

LOCAL_SOURCE_HINTS = (
    "togo",
    "emploi_tg",
    "anpe",
    "miabejob",
    "emploitogo",
    "lucreatif",
    "jobinfotogo",
    "goafrica",
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _local_priority_bonus(site_ids: list[str], source_type: str) -> float:
    if source_type == "api":
        return 0.0
    for site_id in site_ids:
        low = str(site_id).lower()
        if any(hint in low for hint in LOCAL_SOURCE_HINTS):
            return 12.0
    return 0.0


@dataclass
class TargetConfig:
    target_name: str
    source_type: str  # "scrapy" or "api"
    priority: int
    site_ids: list[str]
    base_interval_minutes: int


def _group_targets() -> dict[str, TargetConfig]:
    grouped: dict[str, TargetConfig] = {}

    for site_id, info in get_spider_sites().items():
        spider = str(info.get("spider") or "").strip()
        if not spider:
            continue
        priority = int(info.get("priority") or PRIORITY_LOW)
        current = grouped.get(spider)
        if current is None:
            grouped[spider] = TargetConfig(
                target_name=spider,
                source_type="scrapy",
                priority=priority,
                site_ids=[site_id],
                base_interval_minutes=PRIORITY_INTERVAL_MINUTES.get(priority, 24 * 60),
            )
        else:
            current.site_ids.append(site_id)
            if priority < current.priority:
                current.priority = priority
                current.base_interval_minutes = PRIORITY_INTERVAL_MINUTES.get(priority, 24 * 60)

    api_sites = get_api_sites()
    if api_sites:
        # Agrégateur API exécuté en un seul job.
        priority = min(int(info.get("priority") or PRIORITY_MEDIUM) for info in api_sites.values())
        grouped["api_aggregator"] = TargetConfig(
            target_name="api_aggregator",
            source_type="api",
            priority=priority,
            site_ids=sorted(api_sites.keys()),
            base_interval_minutes=PRIORITY_INTERVAL_MINUTES.get(priority, 12 * 60),
        )

    return grouped


def _extract_qa_health(latest_report: dict[str, Any]) -> tuple[float | None, list[str]]:
    qa = latest_report.get("qa")
    if not isinstance(qa, dict):
        return None, []
    total = _safe_int(qa.get("total"))
    if total <= 0:
        return None, []

    issues: list[str] = []
    date_iso = _safe_int(qa.get("date_iso"))
    apply_method = _safe_int(qa.get("apply_method"))
    description_ok = _safe_int(qa.get("description_ok"))

    date_rate = date_iso / total
    apply_rate = apply_method / total
    desc_rate = description_ok / total

    if date_rate < 0.5 and total >= 5:
        issues.append("low_date_coverage")
    if apply_rate < 0.5 and total >= 5:
        issues.append("low_apply_coverage")
    if desc_rate < 0.8 and total >= 5:
        issues.append("low_description_coverage")

    # Composite QA health score [0,1]
    score = (0.4 * date_rate) + (0.3 * apply_rate) + (0.3 * desc_rate)
    return round(score, 4), issues


def _compute_target_plan(
    cfg: TargetConfig,
    reports: Iterable[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    rows = list(reports)
    latest = rows[0] if rows else None

    last_run_at = None
    last_success_at = None
    last_nonzero_success_at = None
    consecutive_failures = 0
    consecutive_zero_success = 0
    success_count = 0
    error_count = 0

    for row in rows:
        ts = _parse_dt(row.get("timestamp_utc") or row.get("recorded_at"))
        status = str(row.get("status") or "unknown").lower()
        items = _safe_int(row.get("items"))
        if last_run_at is None:
            last_run_at = ts
        if status == "success":
            success_count += 1
            if last_success_at is None:
                last_success_at = ts
            if items > 0 and last_nonzero_success_at is None:
                last_nonzero_success_at = ts
            if consecutive_failures == 0:
                # only count zero-success streak at the beginning
                if items <= 0:
                    consecutive_zero_success += 1
                else:
                    consecutive_zero_success = 0
            if consecutive_failures == 0 and items > 0:
                # once we find a non-zero success in the most recent streak, stop zero streak growth
                pass
        else:
            error_count += 1
            if success_count == 0:
                consecutive_failures += 1

    base_interval = max(15, int(cfg.base_interval_minutes))
    adjusted_interval = base_interval
    status = str((latest or {}).get("status") or "never")
    latest_items = _safe_int((latest or {}).get("items"))

    # Exponential-ish backoff on repeated failures/timeouts.
    if consecutive_failures > 0:
        adjusted_interval = min(base_interval * (2 ** min(consecutive_failures, 3)), 48 * 60)
    # If source recently returns zero items repeatedly, keep checking but not too aggressively.
    elif consecutive_zero_success >= 2:
        adjusted_interval = max(60, min(base_interval, 6 * 60))

    qa_health, qa_issues = _extract_qa_health(latest or {})

    last_ref = last_success_at or last_run_at
    minutes_since_last = None
    if last_ref is not None:
        minutes_since_last = max(0.0, (now - last_ref).total_seconds() / 60.0)

    due = False
    due_reason = ""
    if latest is None:
        due = True
        due_reason = "never_run"
    elif last_ref is None:
        due = True
        due_reason = "invalid_last_timestamp"
    elif minutes_since_last is None:
        due = True
        due_reason = "no_last_reference"
    elif minutes_since_last >= adjusted_interval:
        due = True
        if consecutive_failures > 0:
            due_reason = "retry_backoff_elapsed"
        elif consecutive_zero_success >= 2:
            due_reason = "zero_items_recheck_due"
        else:
            due_reason = "freshness_interval_elapsed"
    else:
        due = False
        due_reason = "not_due"

    # Build a priority/urgency score for ordering.
    overdue_ratio = 0.0
    if minutes_since_last is not None and adjusted_interval > 0:
        overdue_ratio = max(0.0, (minutes_since_last - adjusted_interval) / adjusted_interval)
    score = PRIORITY_WEIGHTS.get(cfg.priority, 10.0)
    score += min(50.0, overdue_ratio * 30.0)
    score += min(40.0, consecutive_failures * 12.0)
    score += _local_priority_bonus(cfg.site_ids, cfg.source_type)
    if latest_items == 0 and status == "success":
        score += 8.0
    if qa_health is not None:
        score += max(0.0, (0.75 - qa_health) * 20.0)

    bandit = score_for_target(cfg.target_name)
    score += float(bandit.get("bonus") or 0.0)

    next_due_at = None
    if last_ref is not None:
        next_due_at = last_ref + timedelta(minutes=adjusted_interval)

    needs_attention = bool(consecutive_failures >= 2 or qa_issues)

    return {
        "target": cfg.target_name,
        "source_type": cfg.source_type,
        "priority": cfg.priority,
        "site_ids": sorted(cfg.site_ids),
        "base_interval_minutes": base_interval,
        "adjusted_interval_minutes": adjusted_interval,
        "latest_status": status,
        "latest_items": latest_items,
        "latest_duration_seconds": _safe_float((latest or {}).get("duration_seconds")),
        "consecutive_failures": consecutive_failures,
        "consecutive_zero_success": consecutive_zero_success,
        "minutes_since_last_ref": round(minutes_since_last, 2) if minutes_since_last is not None else None,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "last_success_at": last_success_at.isoformat() if last_success_at else None,
        "last_nonzero_success_at": (
            last_nonzero_success_at.isoformat() if last_nonzero_success_at else None
        ),
        "qa_health": qa_health,
        "qa_issues": qa_issues,
        "needs_attention": needs_attention,
        "due": due,
        "due_reason": due_reason,
        "next_due_at": next_due_at.isoformat() if next_due_at else None,
        "urgency_score": round(score, 3),
        "bandit_avg_reward": float(bandit.get("avg_reward") or 0.5),
        "bandit_pulls": int(bandit.get("pulls") or 0),
        "bandit_bonus": float(bandit.get("bonus") or 0.0),
        "bandit_randomized": bool(bandit.get("randomized")),
    }


def build_autoplan(
    *,
    max_targets: int = 5,
    include_deferred: bool = True,
    lookback_reports: int = 400,
    force: bool = False,
) -> dict[str, Any]:
    """
    Build an adaptive execution plan for sourcing targets (spiders + api_aggregator).

    A target is considered "due" based on:
    - registry priority (base freshness interval)
    - recent failures/timeouts (backoff)
    - repeated zero-item runs (recheck cadence)
    - QA issues (flagged for attention)
    """
    now = _now_utc()
    all_reports = read_scrape_reports(limit=max(50, min(lookback_reports, 5000)))
    bandit_snapshot = update_bandit_with_reports(all_reports)
    targets = _group_targets()

    # Group reports by spider/source target
    reports_by_target: dict[str, list[dict[str, Any]]] = {}
    for row in all_reports:
        key = str(row.get("spider") or "unknown")
        reports_by_target.setdefault(key, []).append(row)

    plans = [
        _compute_target_plan(cfg, reports_by_target.get(cfg.target_name, []), now)
        for cfg in targets.values()
    ]
    plans_sorted = sorted(plans, key=lambda x: (x["due"] is False, -_safe_float(x["urgency_score"])))

    due_targets = [p for p in plans_sorted if p.get("due")]
    deferred_targets = [p for p in plans_sorted if not p.get("due")]
    if force:
        due_targets = plans_sorted[:]  # force execution candidate list
        for row in due_targets:
            row["forced"] = True
            if not row.get("due"):
                row["due_reason"] = "forced_manual_run"

    selected = due_targets[: max(1, int(max_targets))]
    selected_names = [str(p["target"]) for p in selected]
    attention = [p for p in plans_sorted if p.get("needs_attention")]

    payload: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "total_targets": len(plans_sorted),
        "due_total": len(due_targets),
        "selected_count": len(selected),
        "selected_targets": selected_names,
        "selected": selected,
        "attention": attention[:20],
        "autonomy_notes": {
            "policy": "priority+freshness+backoff+qa+bandit",
            "base_intervals_minutes": PRIORITY_INTERVAL_MINUTES,
        },
        "bandit": {
            "policy": bandit_snapshot.get("policy"),
            "epsilon": bandit_snapshot.get("epsilon"),
            "updated_at": bandit_snapshot.get("updated_at"),
            "tracked_targets": bandit_snapshot.get("tracked_targets"),
            "avg_reward_global": bandit_snapshot.get("avg_reward_global"),
        },
    }
    if include_deferred:
        payload["deferred"] = deferred_targets
    return payload
