from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

_STATE_PATH = Path(
    os.getenv("SEARCH_INDEX_MAINTENANCE_STATE_PATH", "/tmp/search_index_maintenance_state.json")
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read() -> Dict[str, Any]:
    if not _STATE_PATH.exists():
        return {
            "active": False,
            "reason": "",
            "started_at": None,
            "expected_end_at": None,
            "updated_at": _now_iso(),
        }
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "active": False,
            "reason": "",
            "started_at": None,
            "expected_end_at": None,
            "updated_at": _now_iso(),
        }


def _safe_write(payload: Dict[str, Any]) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_maintenance_state() -> Dict[str, Any]:
    state = _safe_read()
    expected_end_at = state.get("expected_end_at")
    if state.get("active") and expected_end_at:
        try:
            end_dt = datetime.fromisoformat(str(expected_end_at))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > end_dt:
                state["active"] = False
                state["reason"] = "expired_auto_clear"
                state["updated_at"] = _now_iso()
                _safe_write(state)
        except Exception:
            pass
    return state


def set_maintenance(active: bool, reason: str = "", duration_minutes: int | None = None) -> Dict[str, Any]:
    state = get_maintenance_state()
    now = datetime.now(timezone.utc)
    state["active"] = bool(active)
    state["reason"] = reason or state.get("reason") or ""
    if active:
        state["started_at"] = now.isoformat()
        if duration_minutes and duration_minutes > 0:
            state["expected_end_at"] = (now + timedelta(minutes=duration_minutes)).isoformat()
        else:
            state["expected_end_at"] = None
    else:
        state["expected_end_at"] = None
    state["updated_at"] = _now_iso()
    _safe_write(state)
    return state
