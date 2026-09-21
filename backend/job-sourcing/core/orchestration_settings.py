# Gestion des parametres d'orchestration Airflow.
# Permet de modifier les crons et l'activation des DAGs via API.

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

from .registry_constants import (
    CRON_MAP,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_NIGHTLY,
)

PRIORITIES = [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_NIGHTLY]

PRIORITY_TO_DAG_ID = {
    PRIORITY_HIGH: "sourcing_priority_1_high_frequency",
    PRIORITY_MEDIUM: "sourcing_priority_2_medium_frequency",
    PRIORITY_LOW: "sourcing_priority_3_low_frequency",
    PRIORITY_NIGHTLY: "sourcing_full_crawl_nightly",
}

_LOCK = threading.Lock()


def _state_file_path() -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    default_path = base_dir / "data" / "orchestration_settings.json"
    raw = os.getenv("ORCHESTRATION_SETTINGS_FILE", str(default_path))
    return Path(raw)


def _default_state() -> Dict[str, Dict[str, Any]]:
    return {
        "priority_crons": {str(priority): CRON_MAP[priority] for priority in PRIORITIES},
        "dag_enabled": {
            dag_id: dag_id != PRIORITY_TO_DAG_ID[PRIORITY_LOW]
            for dag_id in PRIORITY_TO_DAG_ID.values()
        },
    }


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_state(raw: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    state = _default_state()
    if not isinstance(raw, dict):
        return state

    raw_crons = raw.get("priority_crons", {})
    if isinstance(raw_crons, dict):
        for priority in PRIORITIES:
            key = str(priority)
            cron = raw_crons.get(key)
            if isinstance(cron, str) and cron.strip():
                state["priority_crons"][key] = cron.strip()

    raw_enabled = raw.get("dag_enabled", {})
    if isinstance(raw_enabled, dict):
        for dag_id in PRIORITY_TO_DAG_ID.values():
            if dag_id in raw_enabled:
                state["dag_enabled"][dag_id] = bool(raw_enabled[dag_id])

    return state


def _load_state() -> Dict[str, Dict[str, Any]]:
    path = _state_file_path()
    if not path.exists():
        return _default_state()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()

    return _normalize_state(data)


def _save_state(state: Dict[str, Dict[str, Any]]) -> None:
    path = _state_file_path()
    _ensure_parent_dir(path)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _validate_cron(cron: str) -> None:
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError(f"Cron invalide '{cron}': 5 champs attendus.")


def update_orchestration_settings(
    priority_crons: Dict[str, str] | None = None,
    dag_enabled: Dict[str, bool] | None = None,
) -> Dict[str, Any]:
    with _LOCK:
        state = _load_state()

        if priority_crons:
            for key, cron in priority_crons.items():
                if key not in state["priority_crons"]:
                    raise ValueError(f"Priorite inconnue: {key}")
                if not isinstance(cron, str) or not cron.strip():
                    raise ValueError(f"Cron vide pour priorite {key}")
                cron_text = cron.strip()
                _validate_cron(cron_text)
                state["priority_crons"][key] = cron_text

        if dag_enabled:
            for dag_id, enabled in dag_enabled.items():
                if dag_id not in state["dag_enabled"]:
                    raise ValueError(f"DAG inconnu: {dag_id}")
                state["dag_enabled"][dag_id] = bool(enabled)

        _save_state(state)
        return build_orchestration_settings(state)


def get_priority_cron_map() -> Dict[int, str]:
    state = _load_state()
    return {
        priority: state["priority_crons"][str(priority)]
        for priority in PRIORITIES
    }


def get_dag_enabled_by_priority() -> Dict[int, bool]:
    state = _load_state()
    result: Dict[int, bool] = {}
    for priority, dag_id in PRIORITY_TO_DAG_ID.items():
        result[priority] = bool(state["dag_enabled"].get(dag_id, True))
    return result


def _hours_from_cron(cron: str) -> list[str]:
    parts = cron.split()
    if len(parts) != 5:
        return ["cron-custom"]

    minute = parts[0]
    hour_field = parts[1]
    if not minute.isdigit():
        return ["cron-custom"]

    if hour_field.isdigit():
        return [f"{hour_field.zfill(2)}:{minute.zfill(2)}"]

    if "," in hour_field:
        hours = []
        for raw_hour in hour_field.split(","):
            if raw_hour.isdigit():
                hours.append(f"{raw_hour.zfill(2)}:{minute.zfill(2)}")
            else:
                return ["cron-custom"]
        return hours

    return ["cron-custom"]


def _frequency_label(cron: str) -> str:
    hours = _hours_from_cron(cron)
    if hours == ["cron-custom"]:
        return f"Cron personnalise ({cron})"

    count = len(hours)
    if count == 1:
        return "1 fois par jour"
    return f"{count} fois par jour"


def build_orchestration_settings(state: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    current = state or _load_state()
    priority_schedule: Dict[str, Dict[str, Any]] = {}
    for priority in PRIORITIES:
        key = str(priority)
        cron = current["priority_crons"][key]
        dag_id = PRIORITY_TO_DAG_ID[priority]
        priority_schedule[key] = {
            "priority": priority,
            "dag_id": dag_id,
            "cron": cron,
            "hours": _hours_from_cron(cron),
            "frequency": _frequency_label(cron),
            "enabled": bool(current["dag_enabled"].get(dag_id, True)),
        }

    return {
        "priority_crons": dict(current["priority_crons"]),
        "dag_enabled": dict(current["dag_enabled"]),
        "priority_schedule": priority_schedule,
    }


def get_orchestration_settings() -> Dict[str, Any]:
    return build_orchestration_settings()
