"""Automatic QA alerting for sourcing data quality degradation."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from .sourcing_reports import build_qa_summary


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, "true" if default else "false")).strip().lower() in {
        "1", "true", "yes", "on"
    }


def _alert_state_path() -> Path:
    env_path = os.getenv("QA_ALERT_STATE_PATH", "").strip()
    if env_path:
        path = Path(env_path)
    else:
        path = Path(__file__).resolve().parent.parent / "logs" / "qa_alert_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_state() -> dict[str, Any]:
    path = _alert_state_path()
    if not path.exists():
        return {"sent": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"sent": {}}


def _write_state(state: dict[str, Any]) -> None:
    _alert_state_path().write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@dataclass
class QaThresholds:
    min_items: int
    date_iso_rate_min: float
    apply_method_rate_min: float
    description_ok_rate_min: float
    success_rate_min: float
    cooldown_minutes: int


def _thresholds() -> QaThresholds:
    return QaThresholds(
        min_items=_env_int("QA_ALERT_MIN_ITEMS", 5),
        date_iso_rate_min=_env_float("QA_ALERT_DATE_RATE_MIN", 0.50),
        apply_method_rate_min=_env_float("QA_ALERT_APPLY_RATE_MIN", 0.50),
        description_ok_rate_min=_env_float("QA_ALERT_DESCRIPTION_RATE_MIN", 0.80),
        success_rate_min=_env_float("QA_ALERT_SUCCESS_RATE_MIN", 0.70),
        cooldown_minutes=_env_int("QA_ALERT_COOLDOWN_MINUTES", 360),
    )


def _iso_to_dt(text: Any) -> datetime | None:
    if not text:
        return None
    value = str(text)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _rate(qa: dict[str, Any], key: str) -> float | None:
    try:
        total = int(qa.get("total") or 0)
    except Exception:
        total = 0
    if total <= 0:
        return None
    try:
        return float(qa.get(key, 0)) / total
    except Exception:
        return None


def build_qa_alert_preview(*, limit: int = 300) -> dict[str, Any]:
    summary = build_qa_summary(limit=limit)
    thresholds = _thresholds()
    now = _now_utc()
    candidates: list[dict[str, Any]] = []

    for spider, info in (summary.get("spiders") or {}).items():
        latest_status = str(info.get("latest_status") or "unknown")
        latest_items = int(info.get("latest_items") or 0)
        latest_qa = info.get("latest_qa") or {}
        latest_run = info.get("latest_run")
        success_rate = float(info.get("success_rate") or 0.0)

        issues: list[dict[str, Any]] = []

        if latest_status in {"error", "timeout"}:
            issues.append(
                {
                    "code": f"runtime_{latest_status}",
                    "severity": "high",
                    "message": f"Dernier run en {latest_status}",
                }
            )
        elif latest_status == "partial":
            issues.append(
                {
                    "code": "runtime_partial",
                    "severity": "medium",
                    "message": "Dernier run partiel (erreurs detectees)",
                }
            )

        if success_rate < thresholds.success_rate_min and (info.get("runs") or 0) >= 3:
            issues.append(
                {
                    "code": "low_success_rate",
                    "severity": "high" if success_rate < 0.4 else "medium",
                    "message": f"Taux de succes faible ({success_rate:.0%})",
                    "value": round(success_rate, 4),
                }
            )

        if latest_items >= thresholds.min_items and isinstance(latest_qa, dict) and latest_qa.get("total"):
            date_rate = _rate(latest_qa, "date_iso")
            apply_rate = _rate(latest_qa, "apply_method")
            desc_rate = _rate(latest_qa, "description_ok")

            if date_rate is not None and date_rate < thresholds.date_iso_rate_min:
                issues.append(
                    {
                        "code": "low_date_coverage",
                        "severity": "high" if date_rate < 0.3 else "medium",
                        "message": f"Couverture dates faible ({date_rate:.0%})",
                        "value": round(date_rate, 4),
                    }
                )
            if apply_rate is not None and apply_rate < thresholds.apply_method_rate_min:
                issues.append(
                    {
                        "code": "low_apply_coverage",
                        "severity": "high" if apply_rate < 0.3 else "medium",
                        "message": f"Couverture candidature faible ({apply_rate:.0%})",
                        "value": round(apply_rate, 4),
                    }
                )
            if desc_rate is not None and desc_rate < thresholds.description_ok_rate_min:
                issues.append(
                    {
                        "code": "low_description_coverage",
                        "severity": "high" if desc_rate < 0.5 else "medium",
                        "message": f"Couverture description faible ({desc_rate:.0%})",
                        "value": round(desc_rate, 4),
                    }
                )

        if issues:
            candidates.append(
                {
                    "spider": spider,
                    "latest_run": latest_run,
                    "latest_status": latest_status,
                    "latest_items": latest_items,
                    "success_rate": round(success_rate, 4),
                    "issues": issues,
                    "qa": latest_qa if isinstance(latest_qa, dict) else {},
                    "detected_at": now.isoformat(),
                }
            )

    candidates.sort(
        key=lambda c: (
            -max(2 if i.get("severity") == "high" else 1 for i in c["issues"]),
            c["spider"],
        )
    )
    return {
        "generated_at": now.isoformat(),
        "thresholds": thresholds.__dict__,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "summary": summary,
    }


def _alert_key(spider: str, issue_code: str) -> str:
    return f"{spider}:{issue_code}"


def _cooldown_remaining(last_sent_iso: str | None, cooldown_minutes: int) -> int:
    if not last_sent_iso:
        return 0
    dt = _iso_to_dt(last_sent_iso)
    if dt is None:
        return 0
    remaining = (dt + timedelta(minutes=cooldown_minutes)) - _now_utc()
    return max(0, int(remaining.total_seconds()))


def _format_alert_message(alerts: list[dict[str, Any]]) -> str:
    lines = ["TalentFlow QA Alerts (sourcing)", ""]
    for entry in alerts:
        lines.append(f"- {entry['spider']} ({entry.get('latest_status')}, items={entry.get('latest_items', 0)})")
        for issue in entry.get("issues", []):
            sev = str(issue.get("severity", "medium")).upper()
            lines.append(f"  [{sev}] {issue.get('code')}: {issue.get('message')}")
        latest_run = entry.get("latest_run")
        if latest_run:
            lines.append(f"  last_run: {latest_run}")
        lines.append("")
    return "\n".join(lines).strip()


def _send_telegram(text: str) -> dict[str, Any]:
    token = os.getenv("QA_ALERT_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("QA_ALERT_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"enabled": False, "sent": False, "reason": "missing_credentials"}

    payload = urlparse.urlencode({"chat_id": chat_id, "text": text})
    req = urlrequest.Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        return {"enabled": True, "sent": True, "status": getattr(resp, "status", 200), "body": body[:200]}
    except urlerror.URLError as err:
        return {"enabled": True, "sent": False, "reason": str(err)}


def _send_email(text: str) -> dict[str, Any]:
    host = os.getenv("QA_ALERT_SMTP_HOST", "").strip()
    to_addr = os.getenv("QA_ALERT_EMAIL_TO", "").strip()
    from_addr = os.getenv("QA_ALERT_EMAIL_FROM", "").strip() or os.getenv("QA_ALERT_SMTP_USER", "").strip()
    if not host or not to_addr or not from_addr:
        return {"enabled": False, "sent": False, "reason": "missing_smtp_config"}

    port = _env_int("QA_ALERT_SMTP_PORT", 587)
    user = os.getenv("QA_ALERT_SMTP_USER", "").strip()
    password = os.getenv("QA_ALERT_SMTP_PASSWORD", "").strip()
    starttls = _env_flag("QA_ALERT_SMTP_STARTTLS", True)

    msg = EmailMessage()
    msg["Subject"] = "[TalentFlow] QA alert sourcing"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(text)

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            if starttls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return {"enabled": True, "sent": True}
    except Exception as err:
        return {"enabled": True, "sent": False, "reason": str(err)}


def run_qa_alert_check(
    *,
    limit: int = 300,
    notify: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """
    Evaluate QA degradation and optionally send notifications (Telegram/Email).
    Cooldown prevents repeated alerts for the same spider/issue.
    """
    preview = build_qa_alert_preview(limit=limit)
    state = _read_state()
    sent_state = state.setdefault("sent", {})
    thresholds = _thresholds()

    ready_to_send: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    now_iso = _now_utc().isoformat()

    for entry in preview.get("candidates", []):
        spider = str(entry.get("spider"))
        active_issues = []
        suppressed_issues = []
        for issue in entry.get("issues", []):
            key = _alert_key(spider, str(issue.get("code")))
            last_sent = None
            if isinstance(sent_state.get(key), dict):
                last_sent = sent_state[key].get("last_sent_at")
            remaining = 0 if force else _cooldown_remaining(last_sent, thresholds.cooldown_minutes)
            if remaining > 0:
                suppressed_issues.append({**issue, "cooldown_remaining_seconds": remaining})
            else:
                active_issues.append(issue)

        if active_issues:
            ready_to_send.append({**entry, "issues": active_issues})
        if suppressed_issues:
            suppressed.append({**entry, "issues": suppressed_issues})

    delivery: dict[str, Any] = {"notify": notify, "channels": {}}
    if notify and ready_to_send:
        text = _format_alert_message(ready_to_send)
        channels = [c.strip().lower() for c in os.getenv("QA_ALERT_CHANNELS", "telegram,email").split(",") if c.strip()]
        if "telegram" in channels:
            delivery["channels"]["telegram"] = _send_telegram(text)
        if "email" in channels:
            delivery["channels"]["email"] = _send_email(text)

        # Mark as sent only if at least one enabled channel succeeded.
        any_sent = any(bool((r or {}).get("sent")) for r in delivery["channels"].values())
        if any_sent:
            for entry in ready_to_send:
                spider = str(entry.get("spider"))
                for issue in entry.get("issues", []):
                    key = _alert_key(spider, str(issue.get("code")))
                    sent_state[key] = {
                        "last_sent_at": now_iso,
                        "severity": issue.get("severity"),
                        "message": issue.get("message"),
                    }
            state["updated_at"] = now_iso
            _write_state(state)
    elif notify:
        delivery["channels"] = {}

    return {
        "generated_at": preview.get("generated_at"),
        "thresholds": preview.get("thresholds"),
        "candidate_count": preview.get("candidate_count", 0),
        "ready_to_send_count": len(ready_to_send),
        "suppressed_count": len(suppressed),
        "alerts": ready_to_send,
        "suppressed": suppressed,
        "delivery": delivery,
    }

