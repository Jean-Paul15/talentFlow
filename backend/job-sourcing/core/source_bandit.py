"""Persistent contextual bandit utilities for source prioritization."""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path() -> Path:
    raw = os.getenv("SOURCE_BANDIT_STATE_PATH", "").strip()
    if raw:
        path = Path(raw)
    else:
        path = Path(__file__).resolve().parent.parent / "data" / "source_bandit_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _events_path() -> Path:
    raw = os.getenv("SOURCE_BANDIT_EVENTS_PATH", "").strip()
    if raw:
        path = Path(raw)
    else:
        path = Path(__file__).resolve().parent.parent / "logs" / "source_bandit_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "epsilon": float(os.getenv("SOURCE_BANDIT_EPSILON", "0.15")),
        "last_event_keys": [],
        "arms": {},
        "updated_at": _now_iso(),
    }


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return _default_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default_state()
        state = _default_state()
        state.update(raw)
        if not isinstance(state.get("arms"), dict):
            state["arms"] = {}
        if not isinstance(state.get("last_event_keys"), list):
            state["last_event_keys"] = []
        return state
    except Exception:
        return _default_state()


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _now_iso()
    _state_path().write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _target_for_report(report: dict[str, Any]) -> str:
    if str(report.get("source_type") or "").lower() == "api":
        return "api_aggregator"
    target = str(report.get("spider") or "").strip()
    return target or "unknown"


def _event_key(report: dict[str, Any]) -> str:
    seed = "|".join(
        [
            str(report.get("spider") or ""),
            str(report.get("timestamp_utc") or report.get("recorded_at") or ""),
            str(report.get("status") or ""),
            str(report.get("items") or 0),
            str(report.get("errors") or 0),
            str(report.get("source_type") or ""),
        ]
    )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def _compute_reward(report: dict[str, Any]) -> float:
    status = str(report.get("status") or "").lower()
    success = 1.0 if status == "success" else 0.0
    items = max(0, int(report.get("items") or 0))
    errors = max(0, int(report.get("errors") or 0))

    qa = report.get("qa")
    qa_score = 0.5
    if isinstance(qa, dict):
        total = max(1, int(qa.get("total") or 0))
        date_rate = max(0.0, min(1.0, float(qa.get("date_iso") or 0) / total))
        apply_rate = max(0.0, min(1.0, float(qa.get("apply_method") or 0) / total))
        desc_rate = max(0.0, min(1.0, float(qa.get("description_ok") or 0) / total))
        qa_score = (0.4 * date_rate) + (0.3 * apply_rate) + (0.3 * desc_rate)

    items_score = min(1.0, items / 20.0)
    error_penalty = min(0.4, errors * 0.08)
    reward = (0.45 * success) + (0.25 * items_score) + (0.30 * qa_score) - error_penalty
    return round(max(0.0, min(1.0, reward)), 4)


def update_bandit_with_reports(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """
    Update persistent bandit state from scrape reports.
    Reports can be newest-first or oldest-first; duplicate events are ignored.
    """
    rows = [r for r in reports if isinstance(r, dict)]
    if not rows:
        return snapshot_bandit()

    with _LOCK:
        state = _load_state()
        seen = set(str(x) for x in state.get("last_event_keys") or [])
        arms = state.setdefault("arms", {})
        events_path = _events_path()
        updated = 0

        for row in reversed(rows):
            key = _event_key(row)
            if key in seen:
                continue
            seen.add(key)
            updated += 1

            target = _target_for_report(row)
            reward = _compute_reward(row)
            arm = arms.setdefault(
                target,
                {
                    "target": target,
                    "pulls": 0,
                    "reward_sum": 0.0,
                    "avg_reward": 0.5,
                    "last_reward": None,
                    "updated_at": None,
                },
            )
            pulls = int(arm.get("pulls") or 0) + 1
            reward_sum = float(arm.get("reward_sum") or 0.0) + reward
            avg = reward_sum / pulls
            arm.update(
                {
                    "pulls": pulls,
                    "reward_sum": round(reward_sum, 6),
                    "avg_reward": round(avg, 6),
                    "last_reward": reward,
                    "updated_at": _now_iso(),
                }
            )

            with events_path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "timestamp": _now_iso(),
                            "event_key": key,
                            "target": target,
                            "reward": reward,
                            "items": int(row.get("items") or 0),
                            "errors": int(row.get("errors") or 0),
                            "status": str(row.get("status") or ""),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        state["last_event_keys"] = list(seen)[-500:]
        _save_state(state)

    snap = snapshot_bandit()
    snap["updated_events"] = updated
    return snap


def score_for_target(target: str) -> dict[str, float | int | bool]:
    with _LOCK:
        state = _load_state()
    epsilon = float(state.get("epsilon") or 0.15)
    arms = state.get("arms") or {}
    arm = arms.get(target) or {}
    pulls = int(arm.get("pulls") or 0)
    avg_reward = float(arm.get("avg_reward") or 0.5)

    randomize = random.random() < epsilon
    if randomize:
        sampled = random.uniform(0.35, 0.95)
    else:
        sampled = avg_reward

    exploration_boost = max(0.0, (5 - pulls) * 0.08)
    normalized = max(0.0, min(1.0, sampled + exploration_boost))
    bonus = round((normalized - 0.5) * 24.0, 3)
    return {
        "pulls": pulls,
        "avg_reward": round(avg_reward, 4),
        "sampled_reward": round(sampled, 4),
        "exploration_boost": round(exploration_boost, 4),
        "bonus": bonus,
        "randomized": randomize,
    }


def snapshot_bandit() -> dict[str, Any]:
    with _LOCK:
        state = _load_state()
    arms = state.get("arms") or {}
    ordered = sorted(
        [value for value in arms.values() if isinstance(value, dict)],
        key=lambda x: float(x.get("avg_reward") or 0.0),
        reverse=True,
    )
    total_pulls = sum(int(x.get("pulls") or 0) for x in ordered)
    avg_reward_global = round(
        (
            sum(float(x.get("reward_sum") or 0.0) for x in ordered) / max(1, total_pulls)
            if ordered
            else 0.0
        ),
        4,
    )
    return {
        "policy": "epsilon_greedy",
        "epsilon": float(state.get("epsilon") or 0.15),
        "updated_at": state.get("updated_at"),
        "tracked_targets": len(ordered),
        "total_pulls": total_pulls,
        "avg_reward_global": avg_reward_global,
        "arms": ordered[:50],
    }


def reset_bandit() -> dict[str, Any]:
    with _LOCK:
        state = _default_state()
        _save_state(state)
    return snapshot_bandit()
