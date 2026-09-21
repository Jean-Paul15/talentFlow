"""Circuit-breaker helpers for CV text recommendation LLM providers."""

from __future__ import annotations

import time

from .runtime_config import _env_int

__all__ = [
    "_provider_circuit_state",
    "_circuit_failure_threshold",
    "_circuit_reset_seconds",
    "_provider_circuit_can_attempt",
    "_provider_circuit_record_success",
    "_provider_circuit_record_failure",
    "_llm_provider_circuit",
]


def _provider_circuit_state(provider: str) -> dict[str, float | int | str]:
    return _llm_provider_circuit.setdefault(
        provider,
        {"state": "closed", "failures": 0, "opened_at": 0.0},
    )


def _circuit_failure_threshold() -> int:
    return max(1, _env_int("LLM_CIRCUIT_FAILURE_THRESHOLD", 5))


def _circuit_reset_seconds() -> float:
    return max(5.0, float(_env_int("LLM_CIRCUIT_RESET_SECONDS", 60)))


def _provider_circuit_can_attempt(provider: str) -> bool:
    state = _provider_circuit_state(provider)
    if str(state.get("state")) != "open":
        return True
    opened_at = float(state.get("opened_at") or 0.0)
    if time.time() - opened_at >= _circuit_reset_seconds():
        state["state"] = "half_open"
        return True
    return False


def _provider_circuit_record_success(provider: str) -> None:
    state = _provider_circuit_state(provider)
    state["state"] = "closed"
    state["failures"] = 0
    state["opened_at"] = 0.0


def _provider_circuit_record_failure(provider: str) -> None:
    state = _provider_circuit_state(provider)
    failures = int(state.get("failures") or 0) + 1
    state["failures"] = failures
    if failures >= _circuit_failure_threshold():
        state["state"] = "open"
        state["opened_at"] = time.time()


_llm_provider_circuit: dict[str, dict[str, float | int | str]] = {
    "gemini": {"state": "closed", "failures": 0, "opened_at": 0.0},
    "deepseek": {"state": "closed", "failures": 0, "opened_at": 0.0},
}
