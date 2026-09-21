from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from guard_notify import send_email
from guard_store import append_jsonl, now_iso, push_guard_status, read_json, state_dir, toggle_maintenance, write_json

MAP = {
    "health": {"service": "api-gateway", "domain": "global", "deps": ["redis"], "auto_action": True},
    "graphql_reach": {"service": "api-gateway", "domain": "graphql", "deps": ["redis", "postgres"], "auto_action": True},
    "cv_extract_validation": {"service": "recommendation", "domain": "search", "deps": ["search-engine", "redis"], "auto_action": True},
    # ops_status agrège plusieurs dépendances lentes/non critiques ; on le garde en monitoring
    # mais on évite les actions automatiques pour limiter les faux positifs.
    "ops_status": {"service": "api-gateway", "domain": "global", "deps": ["job-sourcing", "search-engine"], "auto_action": False},
}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:  # noqa: BLE001
        return default


COOLDOWN_SECONDS = _env_int("GUARD_ACTION_COOLDOWN_SECONDS", 900)
MAX_ACTIONS_PER_HOUR = _env_int("GUARD_MAX_ACTIONS_PER_HOUR", 10)
LOCK_TTL_SECONDS = _env_int("GUARD_DECISION_LOCK_TTL_SECONDS", 240)
COMPOSE_FILE = os.getenv("GUARD_COMPOSE_FILE", "/opt/talentflow/backend/docker-compose.yml").strip()


def _run(cmd: list[str], timeout: int = 70) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or proc.stderr or "").strip()[:280]
    except Exception as exc:  # noqa: BLE001
        return str(exc)[:280]


def _restart(service: str) -> str:
    return _run(["docker", "compose", "-f", COMPOSE_FILE, "restart", service])


def _acquire_lock(now_ts: int) -> bool:
    state_dir()
    current = read_json("decision.lock.json", {})
    if int(current.get("expiresAt", 0)) > now_ts:
        return False
    write_json("decision.lock.json", {"holder": "decision", "expiresAt": now_ts + LOCK_TTL_SECONDS})
    return True


def _can_act(state: dict[str, Any], service: str, now_ts: int) -> bool:
    cooldown = int((state.get("serviceCooldownUntil") or {}).get(service, 0))
    if cooldown > now_ts:
        return False
    floor = now_ts - 3600
    actions = [a for a in state.get("actions", []) if int(a.get("ts", 0)) >= floor]
    return len(actions) < MAX_ACTIONS_PER_HOUR


def _record_action(state: dict[str, Any], action: dict[str, Any], service: str, now_ts: int) -> None:
    action["ts"] = now_ts
    state.setdefault("actions", []).append(action)
    state.setdefault("serviceCooldownUntil", {})[service] = now_ts + COOLDOWN_SECONDS


def run_decision() -> dict[str, Any]:
    now_ts = int(time.time())
    if not _acquire_lock(now_ts):
        return {"agent": "decision", "generatedAt": now_iso(), "summary": {"skipped": "lock_active"}}

    probe = read_json("probe_critical_latest.json", {})
    state = read_json("decision_state.json", {"incidents": {}, "actions": [], "serviceCooldownUntil": {}})
    incidents = state.setdefault("incidents", {})
    failed = {x.get("endpoint"): x for x in probe.get("results", []) if not x.get("ok")}
    run_actions: list[dict[str, Any]] = []
    open_count = 0
    alerts_sent = 0

    for endpoint, meta in MAP.items():
        inc = incidents.setdefault(endpoint, {"failures": 0, "successes": 0, "stage": 0, "open": False})
        if endpoint in failed:
            inc["failures"] += 1
            inc["successes"] = 0
            if not bool(meta.get("auto_action", True)):
                inc["open"] = True
                open_count += 1
                continue
            if not _can_act(state, meta["service"], now_ts):
                continue
            if inc["failures"] >= 2 and inc["stage"] == 0:
                action = {"at": now_iso(), "type": "restart", "endpoint": endpoint, "service": meta["service"], "output": _restart(meta["service"])}
                inc.update({"stage": 1, "open": True})
            elif inc["failures"] >= 3 and inc["stage"] == 1:
                output = [_restart(meta["service"])] + [_restart(dep) for dep in meta.get("deps", [])]
                action = {"at": now_iso(), "type": "restart_deps", "endpoint": endpoint, "service": meta["service"], "deps": meta.get("deps", []), "output": " | ".join(output)}
                inc["stage"] = 2
            elif inc["failures"] >= 4 and inc["stage"] >= 2:
                toggle_maintenance(meta["domain"], True, "Maintenance en cours. Réessaie dans quelques instants.", retry_after=180)
                _run(["/opt/talentflow-admin/bin/tf-batch-down.sh"], timeout=90)
                action = {"at": now_iso(), "type": "maintenance_on", "endpoint": endpoint, "service": meta["service"], "domain": meta["domain"]}
                inc["stage"] = 3
            else:
                action = {}
            if action:
                _record_action(state, action, meta["service"], now_ts)
                run_actions.append(action)
        else:
            inc["successes"] += 1
            inc["failures"] = 0
            if inc.get("open") and inc["successes"] >= 3:
                toggle_maintenance(meta["domain"], False, "Service rétabli.", retry_after=60)
                action = {"at": now_iso(), "type": "maintenance_off", "endpoint": endpoint, "service": meta["service"], "domain": meta["domain"]}
                inc.update({"open": False, "stage": 0})
                _record_action(state, action, meta["service"], now_ts)
                run_actions.append(action)
        if inc.get("open"):
            open_count += 1

    if run_actions:
        sent = send_email(
            subject="[TalentFlow] Action automatique de stabilité",
            text=f"Actions exécutées: {len(run_actions)}\nIncidents ouverts: {open_count}\nHorodatage: {now_iso()}",
            dedupe_minutes=10,
            severity="critical",
            actions=[
                {"label": "Voir le statut global", "url": "https://api.example.com/runtime/ops-status"},
                {"label": "Ouvrir TalentFlow", "url": "https://app.example.com"},
            ],
        )
        alerts_sent = 1 if sent.get("sent") else 0

    state["updatedAt"] = now_iso()
    state["actions"] = state.get("actions", [])[-300:]
    write_json("decision_state.json", state)
    summary = {
        "agent": "decision",
        "generatedAt": now_iso(),
        "summary": {"openIncidents": open_count, "actionsLastRun": len(run_actions)},
        "actions": run_actions,
        "counters": {
            "incidents_open": open_count,
            "actions_total": len(state["actions"]),
            "actions_restart_total": len([a for a in state["actions"] if a.get("type") == "restart"]),
            "actions_restart_deps_total": len([a for a in state["actions"] if a.get("type") == "restart_deps"]),
            "actions_maintenance_on_total": len([a for a in state["actions"] if a.get("type") == "maintenance_on"]),
            "actions_maintenance_off_total": len([a for a in state["actions"] if a.get("type") == "maintenance_off"]),
            "alerts_email_total": alerts_sent,
        },
    }
    append_jsonl("decision_history.jsonl", summary)
    push_guard_status(summary)
    return summary
