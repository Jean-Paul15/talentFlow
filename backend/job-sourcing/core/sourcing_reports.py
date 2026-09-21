"""Persistence and summaries for sourcing scrape runs (JSONL, file-based)."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

_WRITE_LOCK = threading.Lock()


def _reports_path() -> Path:
    env_path = os.getenv("SCRAPING_REPORTS_PATH", "").strip()
    if env_path:
        path = Path(env_path)
    else:
        path = Path(__file__).resolve().parent.parent / "logs" / "scrape_reports.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_scrape_report(report: dict[str, Any]) -> None:
    """Append one scrape run report to the JSONL file."""
    payload = dict(report)
    payload.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _WRITE_LOCK:
        with _reports_path().open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def read_scrape_reports(
    *,
    limit: int = 100,
    spider: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Read recent reports (newest first)."""
    path = _reports_path()
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if spider and row.get("spider") != spider:
            continue
        if status and row.get("status") != status:
            continue
        if source_type and row.get("source_type") != source_type:
            continue
        rows.append(row)
        if len(rows) >= max(1, min(limit, 1000)):
            break
    return rows


def latest_report_per_spider(
    *,
    limit_per_spider: int = 1,
    include_api: bool = True,
    max_scan: int = 500,
) -> dict[str, list[dict[str, Any]]]:
    """Return the latest N reports per spider/source name."""
    reports = read_scrape_reports(limit=max_scan)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in reports:
        key = str(row.get("spider") or "unknown")
        if not include_api and row.get("source_type") == "api":
            continue
        bucket = grouped.setdefault(key, [])
        if len(bucket) < max(1, limit_per_spider):
            bucket.append(row)
    return grouped


def build_qa_summary(*, limit: int = 300) -> dict[str, Any]:
    """
    Build QA coverage summary from recent reports.
    Focuses on Scrapy spiders where qa metrics exist.
    """
    reports = read_scrape_reports(limit=limit)
    per_spider: dict[str, dict[str, Any]] = {}
    recent_issues: list[dict[str, Any]] = []

    for row in reports:
        spider = str(row.get("spider") or "unknown")
        qa = row.get("qa") or {}
        items = int(row.get("items") or 0)
        errors = int(row.get("errors") or 0)
        status = str(row.get("status") or "unknown")
        bucket = per_spider.setdefault(
            spider,
            {
                "runs": 0,
                "items_total": 0,
                "errors_total": 0,
                "latest_run": None,
                "latest_status": None,
                "latest_items": 0,
                "qa_rate_sums": {
                    "date_iso_rate": 0.0,
                    "deadline_iso_rate": 0.0,
                    "apply_method_rate": 0.0,
                    "description_ok_rate": 0.0,
                },
                "qa_rate_count": 0,
                "latest_qa": qa if isinstance(qa, dict) else {},
            },
        )
        bucket["runs"] += 1
        bucket["items_total"] += items
        bucket["errors_total"] += errors
        if bucket["latest_run"] is None:
            bucket["latest_run"] = row.get("timestamp_utc") or row.get("recorded_at")
            bucket["latest_status"] = status
            bucket["latest_items"] = items
            bucket["latest_qa"] = qa if isinstance(qa, dict) else {}

        qa_rates = _extract_qa_rates(qa)
        if qa_rates:
            bucket["qa_rate_count"] += 1
            for k, v in qa_rates.items():
                bucket["qa_rate_sums"][k] += float(v)

            if (
                (qa_rates.get("date_iso_rate", 1.0) < 0.5 and items >= 5)
                or (qa_rates.get("apply_method_rate", 1.0) < 0.5 and items >= 5)
                or status != "success"
                or errors > 0
            ):
                recent_issues.append(
                    {
                        "spider": spider,
                        "timestamp_utc": row.get("timestamp_utc") or row.get("recorded_at"),
                        "status": status,
                        "items": items,
                        "errors": errors,
                        "qa_rates": qa_rates,
                    }
                )
        elif status != "success" or errors > 0:
            recent_issues.append(
                {
                    "spider": spider,
                    "timestamp_utc": row.get("timestamp_utc") or row.get("recorded_at"),
                    "status": status,
                    "items": items,
                    "errors": errors,
                }
            )

    for spider, bucket in per_spider.items():
        n = max(1, int(bucket.get("qa_rate_count") or 0))
        bucket["qa_rates_avg"] = {
            k: round(v / n, 4) if bucket.get("qa_rate_count") else None
            for k, v in bucket["qa_rate_sums"].items()
        }
        bucket.pop("qa_rate_sums", None)
        bucket["success_rate"] = round(
            _success_rate_for_spider(spider, reports),
            4,
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reports_considered": len(reports),
        "spiders": per_spider,
        "recent_issues": recent_issues[:50],
    }


def _extract_qa_rates(qa: Any) -> dict[str, float]:
    if not isinstance(qa, dict):
        return {}
    total = qa.get("total")
    try:
        total_int = int(total)
    except Exception:
        total_int = 0
    if total_int <= 0:
        return {}

    def _rate(key: str) -> float:
        try:
            return float(qa.get(key, 0)) / total_int
        except Exception:
            return 0.0

    return {
        "date_iso_rate": _rate("date_iso"),
        "deadline_iso_rate": _rate("deadline_iso"),
        "apply_method_rate": _rate("apply_method"),
        "description_ok_rate": _rate("description_ok"),
    }


def _success_rate_for_spider(spider: str, reports: Iterable[dict[str, Any]]) -> float:
    total = 0
    ok = 0
    for row in reports:
        if str(row.get("spider") or "unknown") != spider:
            continue
        total += 1
        if row.get("status") == "success":
            ok += 1
    if total == 0:
        return 0.0
    return ok / total

