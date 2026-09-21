"""Online RL-like policy agent for CV document threshold tuning.

This module implements a lightweight contextual bandit using Beta posteriors
to choose among a few threshold policies. It is intentionally simple, robust,
and file-backed so it works in constrained production environments.
"""

from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class CvRlPolicyDecision:
    arm: str
    cv_threshold: float
    non_cv_threshold: float
    decision_id: str


DEFAULT_ARMS = {
    "strict": {"cv_threshold": 0.68, "non_cv_threshold": 0.36},
    "balanced": {"cv_threshold": 0.62, "non_cv_threshold": 0.42},
    "permissive": {"cv_threshold": 0.58, "non_cv_threshold": 0.46},
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _state_path() -> Path:
    raw = str(os.getenv("CV_DOCUMENT_RL_POLICY_PATH", "")).strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / "data" / "cv_rl_policy_state.json"


def _events_path() -> Path:
    raw = str(os.getenv("CV_DOCUMENT_RL_EVENTS_PATH", "")).strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / "data" / "cv_rl_policy_events.jsonl"


def _default_state() -> dict:
    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "arms": {
            arm: {"alpha": 1.0, "beta": 1.0, "uses": 0, **thresholds}
            for arm, thresholds in DEFAULT_ARMS.items()
        },
    }


def _load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return _default_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
    if not isinstance(payload, dict) or not isinstance(payload.get("arms"), dict):
        return _default_state()
    return payload


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _choose_arm(state: dict) -> str:
    arms = state.get("arms", {})
    if not arms:
        return "balanced"

    epsilon = float(str(os.getenv("CV_DOCUMENT_RL_EPSILON", "0.00")).strip() or "0.00")
    arm_names = list(arms.keys())
    if epsilon > 0 and random.random() < epsilon:
        return random.choice(arm_names)

    best_arm = "balanced"
    best_score = float("-inf")
    for arm, payload in arms.items():
        alpha = float(payload.get("alpha", 1.0))
        beta = float(payload.get("beta", 1.0))
        score = alpha / max(alpha + beta, 1e-9)
        if score > best_score or (abs(score - best_score) <= 1e-9 and arm == "balanced"):
            best_score = score
            best_arm = arm
    return best_arm


def select_cv_rl_policy() -> CvRlPolicyDecision:
    if not _env_bool("CV_DOCUMENT_RL_ENABLED", True):
        arm = "balanced"
        thresholds = DEFAULT_ARMS[arm]
        return CvRlPolicyDecision(
            arm=arm,
            cv_threshold=thresholds["cv_threshold"],
            non_cv_threshold=thresholds["non_cv_threshold"],
            decision_id=f"rl-off-{uuid.uuid4().hex}",
        )

    state = _load_state()
    arm = _choose_arm(state)
    arm_payload = state.get("arms", {}).get(arm, DEFAULT_ARMS["balanced"])
    arm_payload["uses"] = int(arm_payload.get("uses", 0)) + 1
    state.setdefault("arms", {})[arm] = arm_payload
    _save_state(state)

    return CvRlPolicyDecision(
        arm=arm,
        cv_threshold=float(arm_payload.get("cv_threshold", 0.62)),
        non_cv_threshold=float(arm_payload.get("non_cv_threshold", 0.42)),
        decision_id=uuid.uuid4().hex,
    )


def log_cv_rl_decision(
    *,
    decision: CvRlPolicyDecision,
    cv_confidence: float,
    document_kind: str,
    signal_summary: dict[str, int],
) -> None:
    if not _env_bool("CV_DOCUMENT_RL_ENABLED", True):
        return
    path = _events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision_id": decision.decision_id,
        "arm": decision.arm,
        "cv_threshold": decision.cv_threshold,
        "non_cv_threshold": decision.non_cv_threshold,
        "cv_confidence": cv_confidence,
        "document_kind": document_kind,
        "signal_summary": signal_summary,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def apply_cv_rl_reward(arm: str, reward: float) -> None:
    if not _env_bool("CV_DOCUMENT_RL_ENABLED", True):
        return
    reward = max(0.0, min(1.0, float(reward)))
    state = _load_state()
    payload = state.setdefault("arms", {}).setdefault(
        arm,
        {"alpha": 1.0, "beta": 1.0, **DEFAULT_ARMS.get("balanced", {})},
    )
    payload["alpha"] = float(payload.get("alpha", 1.0)) + reward
    payload["beta"] = float(payload.get("beta", 1.0)) + (1.0 - reward)
    state["arms"][arm] = payload
    _save_state(state)
