from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any
from urllib import request

from guard_store import now_iso, read_json, write_json


def _resend_enabled() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip())


def _fingerprint(subject: str, text: str) -> str:
    return hashlib.sha1(f"{subject}|{text}".encode("utf-8")).hexdigest()


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_html(subject: str, text: str, severity: str, actions: list[dict[str, str]] | None) -> str:
    badge = {"critical": "#D92D20", "warning": "#F79009", "info": "#1570EF"}.get(severity, "#1570EF")
    rows = []
    for line in text.splitlines():
        clean = _escape_html(line.strip())
        if clean:
            rows.append(f"<p style='margin:0 0 10px 0;color:#344054;font-size:14px;line-height:1.5'>{clean}</p>")
    action_html = ""
    if actions:
        buttons = []
        for action in actions[:3]:
            label = _escape_html(action.get("label", "Ouvrir"))
            url = _escape_html(action.get("url", "https://app.example.com"))
            buttons.append(
                f"<a href='{url}' style='display:inline-block;margin-right:8px;margin-bottom:8px;"
                "background:#1D2939;color:#FFFFFF;text-decoration:none;padding:10px 14px;border-radius:12px;"
                f"font-size:13px;font-weight:600'>{label}</a>",
            )
        action_html = (
            "<div style='margin-top:14px'>"
            "<p style='margin:0 0 10px 0;color:#475467;font-size:13px'>Actions recommandées</p>"
            + "".join(buttons)
            + "</div>"
        )
    return (
        "<!doctype html><html><body style='margin:0;background:#F5F7FA;font-family:Inter,Segoe UI,Arial,sans-serif'>"
        "<div style='max-width:640px;margin:24px auto;padding:0 12px'>"
        "<div style='background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 12px 40px rgba(16,24,40,.08)'>"
        "<div style='padding:20px 22px;background:linear-gradient(120deg,#111827,#1D2939);'>"
        "<div style='display:flex;align-items:center;justify-content:space-between'>"
        "<div><p style='margin:0;color:#F9FAFB;font-size:12px;letter-spacing:.06em;text-transform:uppercase'>TalentFlow Guard</p>"
        f"<h2 style='margin:6px 0 0 0;color:#fff;font-size:20px;line-height:1.2'>{_escape_html(subject)}</h2></div>"
        f"<span style='background:{badge};color:#fff;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:700'>"
        f"{_escape_html(severity.upper())}</span></div></div>"
        f"<div style='padding:20px 22px'>{''.join(rows)}{action_html}"
        "<hr style='margin:16px 0;border:none;border-top:1px solid #EAECF0'/>"
        "<p style='margin:0;color:#667085;font-size:12px'>Alerte automatique envoyée par le système de stabilité TalentFlow.</p>"
        "</div></div></div></body></html>"
    )


def send_email(
    subject: str,
    text: str,
    *,
    dedupe_minutes: int = 20,
    force: bool = False,
    severity: str = "warning",
    actions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    state = read_json("notify_state.json", {"sent": {}})
    fp = _fingerprint(subject, text[:220])
    now = int(time.time())
    last = int((state.get("sent", {}) or {}).get(fp, 0))
    if not force and now - last < dedupe_minutes * 60:
        return {"ok": False, "sent": False, "reason": "deduped"}
    if not _resend_enabled():
        return {"ok": False, "sent": False, "reason": "missing_resend_key"}

    payload = {
        "from": os.getenv("GUARD_ALERT_FROM", "TalentFlow Alerts <alerts@example.com>"),
        "to": [os.getenv("GUARD_ALERT_TO", "adoglijeanpaul@gmail.com")],
        "subject": subject,
        "text": text,
        "html": _build_html(subject, text, severity, actions),
    }
    req = request.Request("https://api.resend.com/emails", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "TalentFlow-Guard/1.0 (+https://api.example.com)")
    req.add_header("Authorization", f"Bearer {os.getenv('RESEND_API_KEY', '').strip()}")
    req.data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        with request.urlopen(req, timeout=12) as resp:
            _ = resp.read()
        state.setdefault("sent", {})[fp] = now
        state["updatedAt"] = now_iso()
        write_json("notify_state.json", state)
        return {"ok": True, "sent": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "sent": False, "reason": str(exc)[:220]}
