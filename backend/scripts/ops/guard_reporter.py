from __future__ import annotations

import os

from guard_notify import send_email
from guard_store import now_iso, push_guard_status, read_json, write_json


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def run_digest():
    probe = read_json("probe_critical_latest.json", {})
    decision = read_json("decision_state.json", {"incidents": {}, "actions": []})
    failures = [r for r in probe.get("results", []) if not r.get("ok")]
    open_incidents = [k for k, v in (decision.get("incidents") or {}).items() if v.get("open")]

    payload = {
        "agent": "reporter",
        "generatedAt": now_iso(),
        "summary": {
            "failedEndpoints": len(failures),
            "openIncidents": len(open_incidents),
            "trackedEndpoints": len(probe.get("results", [])),
        },
        "failedEndpoints": failures,
        "openIncidents": open_incidents,
        "counters": {
            "digest_failed_endpoints": len(failures),
            "digest_open_incidents": len(open_incidents),
        },
    }
    push_guard_status(payload)

    # Quiet mode by default: no email when everything is healthy.
    send_when_healthy = _env_bool("GUARD_DIGEST_SEND_HEALTHY", False)
    should_notify = bool(failures or open_incidents) or send_when_healthy

    if should_notify:
        severity = "critical" if open_incidents else ("warning" if failures else "info")
        sent = send_email(
            subject="[TalentFlow] Digest stabilité",
            text=(
                f"Horodatage: {payload['generatedAt']}\n"
                f"Endpoints en échec: {len(failures)}\n"
                f"Incidents ouverts: {len(open_incidents)}\n"
            ),
            dedupe_minutes=30,
            force=False,
            severity=severity,
            actions=[
                {"label": "Consulter le statut runtime", "url": "https://api.example.com/runtime/guard/status"},
                {"label": "Ouvrir TalentFlow", "url": "https://app.example.com"},
            ],
        )
        payload["notification"] = {
            "enabled": True,
            "sent": bool(sent.get("sent")),
            "reason": sent.get("reason", ""),
            "severity": severity,
        }
    else:
        payload["notification"] = {
            "enabled": True,
            "sent": False,
            "reason": "healthy_suppressed",
            "severity": "info",
        }

    write_json("digest_latest.json", payload)
    return payload
