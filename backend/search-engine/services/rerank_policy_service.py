from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

from loguru import logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, default)).strip())
    except Exception:
        return float(default)


def _env_str(name: str, default: str) -> str:
    return str(os.getenv(name, default)).strip() or default


class RerankPolicyService:
    """
    Politique de pilotage du reranker:
    - mode manuel: enabled fixe
    - mode auto: active/desactive selon gains observés sur /search/evaluate-batch
    Etat persistant en JSON.
    """

    def __init__(self, *, initial_enabled: bool):
        self._lock = RLock()
        self._reranker = None

        self.mode = _env_str("RERANK_POLICY_MODE", "auto").lower()
        if self.mode not in {"auto", "manual"}:
            self.mode = "auto"

        self.enabled_default = bool(initial_enabled)
        self.target_ndcg_k = _env_int("RERANK_POLICY_TARGET_K", 10)
        self.min_cases_for_decision = _env_int("RERANK_POLICY_MIN_CASES", 3)
        self.enable_ndcg_gain_abs = _env_float("RERANK_POLICY_ENABLE_NDCG_GAIN_ABS", 0.01)
        self.enable_mrr_gain_abs = _env_float("RERANK_POLICY_ENABLE_MRR_GAIN_ABS", 0.005)
        self.disable_ndcg_gain_abs = _env_float("RERANK_POLICY_DISABLE_NDCG_GAIN_ABS", -0.01)
        self.disable_mrr_gain_abs = _env_float("RERANK_POLICY_DISABLE_MRR_GAIN_ABS", -0.005)
        self.enable_windows = max(1, _env_int("RERANK_POLICY_ENABLE_WINDOWS", 2))
        self.disable_windows = max(1, _env_int("RERANK_POLICY_DISABLE_WINDOWS", 1))
        self.max_history = max(10, _env_int("RERANK_POLICY_MAX_HISTORY", 100))
        self.state_file = Path(_env_str("RERANK_POLICY_STATE_FILE", "/tmp/talentflow_rerank_policy.json"))
        self.last_decision_reason = "bootstrap"
        self.updated_at = _now_iso()
        self.history: list[Dict[str, Any]] = []

        self._load_state()

    def bind_reranker(self, reranker: Any) -> None:
        with self._lock:
            self._reranker = reranker
            self._apply_enabled_state()

    def get_state(self, *, history_limit: int = 20) -> Dict[str, Any]:
        with self._lock:
            history_tail = self.history[-max(1, int(history_limit)) :]
            return {
                "mode": self.mode,
                "enabled_default": bool(self.enabled_default),
                "target_ndcg_k": int(self.target_ndcg_k),
                "min_cases_for_decision": int(self.min_cases_for_decision),
                "thresholds": {
                    "enable_ndcg_gain_abs": float(self.enable_ndcg_gain_abs),
                    "enable_mrr_gain_abs": float(self.enable_mrr_gain_abs),
                    "disable_ndcg_gain_abs": float(self.disable_ndcg_gain_abs),
                    "disable_mrr_gain_abs": float(self.disable_mrr_gain_abs),
                },
                "windows": {
                    "enable": int(self.enable_windows),
                    "disable": int(self.disable_windows),
                },
                "last_decision_reason": self.last_decision_reason,
                "updated_at": self.updated_at,
                "history_size": len(self.history),
                "history": history_tail,
            }

    def set_manual(self, *, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            self.mode = "manual"
            self.enabled_default = bool(enabled)
            self.last_decision_reason = "manual_override"
            self.updated_at = _now_iso()
            self._apply_enabled_state()
            self._save_state()
            return self.get_state()

    def set_auto(self) -> Dict[str, Any]:
        with self._lock:
            self.mode = "auto"
            self.last_decision_reason = "auto_mode_enabled"
            self.updated_at = _now_iso()
            self._save_state()
            return self.get_state()

    def update_settings(
        self,
        *,
        target_ndcg_k: Optional[int] = None,
        min_cases_for_decision: Optional[int] = None,
        enable_ndcg_gain_abs: Optional[float] = None,
        enable_mrr_gain_abs: Optional[float] = None,
        disable_ndcg_gain_abs: Optional[float] = None,
        disable_mrr_gain_abs: Optional[float] = None,
        enable_windows: Optional[int] = None,
        disable_windows: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if target_ndcg_k is not None:
                self.target_ndcg_k = max(1, int(target_ndcg_k))
            if min_cases_for_decision is not None:
                self.min_cases_for_decision = max(1, int(min_cases_for_decision))
            if enable_ndcg_gain_abs is not None:
                self.enable_ndcg_gain_abs = float(enable_ndcg_gain_abs)
            if enable_mrr_gain_abs is not None:
                self.enable_mrr_gain_abs = float(enable_mrr_gain_abs)
            if disable_ndcg_gain_abs is not None:
                self.disable_ndcg_gain_abs = float(disable_ndcg_gain_abs)
            if disable_mrr_gain_abs is not None:
                self.disable_mrr_gain_abs = float(disable_mrr_gain_abs)
            if enable_windows is not None:
                self.enable_windows = max(1, int(enable_windows))
            if disable_windows is not None:
                self.disable_windows = max(1, int(disable_windows))
            self.last_decision_reason = "settings_updated"
            self.updated_at = _now_iso()
            self._save_state()
            return self.get_state()

    def record_batch_evaluation(
        self,
        *,
        summary: Dict[str, Any],
        backend: str,
        cases_evaluated: int,
        candidate_pool_size: int,
        rerank_top_k: int,
    ) -> Dict[str, Any]:
        """
        Enregistre une évaluation batch et applique éventuellement la décision auto.
        """
        with self._lock:
            ndcg_map = summary.get("ndcg_gain_abs") or {}
            target_key = str(self.target_ndcg_k)
            ndcg_gain = float(ndcg_map.get(target_key, 0.0) or 0.0)
            mrr_gain = float(summary.get("mrr_gain_abs", 0.0) or 0.0)

            if target_key not in ndcg_map and ndcg_map:
                try:
                    fallback_key = sorted(ndcg_map.keys(), key=lambda x: int(x))[-1]
                    ndcg_gain = float(ndcg_map.get(fallback_key, 0.0) or 0.0)
                except Exception:
                    fallback_key = next(iter(ndcg_map.keys()))
                    ndcg_gain = float(ndcg_map.get(fallback_key, 0.0) or 0.0)
                used_k = str(fallback_key)
            else:
                used_k = target_key

            signal = self._signal_for_window(
                ndcg_gain=ndcg_gain,
                mrr_gain=mrr_gain,
                cases_evaluated=cases_evaluated,
            )
            event = {
                "timestamp": _now_iso(),
                "backend": backend,
                "cases_evaluated": int(cases_evaluated),
                "candidate_pool_size": int(candidate_pool_size),
                "rerank_top_k": int(rerank_top_k),
                "used_ndcg_k": used_k,
                "ndcg_gain_abs": float(ndcg_gain),
                "mrr_gain_abs": float(mrr_gain),
                "signal": signal,
            }
            self.history.append(event)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history :]

            changed = False
            reason = "recorded_no_change"
            if self.mode == "auto":
                changed, reason = self._evaluate_auto_switch()

            self.last_decision_reason = reason
            self.updated_at = _now_iso()
            self._save_state()
            state = self.get_state()
            state["decision_changed"] = changed
            state["decision_reason"] = reason
            return state

    def _signal_for_window(self, *, ndcg_gain: float, mrr_gain: float, cases_evaluated: int) -> str:
        if int(cases_evaluated) < self.min_cases_for_decision:
            return "insufficient_cases"
        if ndcg_gain >= self.enable_ndcg_gain_abs and mrr_gain >= self.enable_mrr_gain_abs:
            return "enable"
        if ndcg_gain <= self.disable_ndcg_gain_abs or mrr_gain <= self.disable_mrr_gain_abs:
            return "disable"
        return "neutral"

    def _evaluate_auto_switch(self) -> tuple[bool, str]:
        enable_streak = self._streak("enable")
        disable_streak = self._streak("disable")

        if not self.enabled_default and enable_streak >= self.enable_windows:
            self.enabled_default = True
            self._apply_enabled_state()
            return True, f"auto_enable_after_{enable_streak}_windows"
        if self.enabled_default and disable_streak >= self.disable_windows:
            self.enabled_default = False
            self._apply_enabled_state()
            return True, f"auto_disable_after_{disable_streak}_windows"
        return False, "auto_no_switch"

    def _streak(self, expected_signal: str) -> int:
        streak = 0
        for item in reversed(self.history):
            signal = str(item.get("signal", "neutral"))
            if signal == "insufficient_cases":
                continue
            if signal == expected_signal:
                streak += 1
            else:
                break
        return streak

    def _apply_enabled_state(self) -> None:
        if self._reranker is None:
            return
        try:
            self._reranker.enabled_by_default = bool(self.enabled_default)
        except Exception as err:
            logger.warning(f"Impossible d'appliquer l'etat rerank par defaut: {err}")

    def _load_state(self) -> None:
        try:
            if not self.state_file.exists():
                return
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            self.mode = str(payload.get("mode", self.mode)).lower()
            if self.mode not in {"auto", "manual"}:
                self.mode = "auto"
            self.enabled_default = bool(payload.get("enabled_default", self.enabled_default))
            self.target_ndcg_k = int(payload.get("target_ndcg_k", self.target_ndcg_k))
            self.min_cases_for_decision = int(payload.get("min_cases_for_decision", self.min_cases_for_decision))
            thresholds = payload.get("thresholds") or {}
            self.enable_ndcg_gain_abs = float(thresholds.get("enable_ndcg_gain_abs", self.enable_ndcg_gain_abs))
            self.enable_mrr_gain_abs = float(thresholds.get("enable_mrr_gain_abs", self.enable_mrr_gain_abs))
            self.disable_ndcg_gain_abs = float(thresholds.get("disable_ndcg_gain_abs", self.disable_ndcg_gain_abs))
            self.disable_mrr_gain_abs = float(thresholds.get("disable_mrr_gain_abs", self.disable_mrr_gain_abs))
            windows = payload.get("windows") or {}
            self.enable_windows = max(1, int(windows.get("enable", self.enable_windows)))
            self.disable_windows = max(1, int(windows.get("disable", self.disable_windows)))
            history = payload.get("history") or []
            if isinstance(history, list):
                self.history = [h for h in history if isinstance(h, dict)][-self.max_history :]
            self.last_decision_reason = str(payload.get("last_decision_reason", self.last_decision_reason))
            self.updated_at = str(payload.get("updated_at", self.updated_at))
        except Exception as err:
            logger.warning(f"Chargement rerank policy state ignore: {err}")

    def _save_state(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = self.get_state(history_limit=self.max_history)
            self.state_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as err:
            logger.warning(f"Sauvegarde rerank policy state ignoree: {err}")
