"""Runtime snapshot helpers for CV text recommendation budgets."""

from __future__ import annotations

import os

from . import budget_queue
from .budget_circuit import _provider_circuit_state
from .budget_cost import _deepseek_get_budget_state
from .runtime_config import _env_bool, _provider_order

__all__ = ["get_llm_runtime_state"]


def get_llm_runtime_state() -> dict:
    deepseek_budget = _deepseek_get_budget_state()
    return {
        "provider_order": _provider_order(),
        "queue": {
            "waiting": int(budget_queue._llm_queue_waiting),
            "active": int(budget_queue._llm_queue_active),
            "max_size": budget_queue._llm_queue_max_size(),
            "wait_ms": int(budget_queue._llm_queue_wait_seconds() * 1000),
            "concurrency": budget_queue._llm_queue_concurrency(),
        },
        "circuit": {
            "gemini": dict(_provider_circuit_state("gemini")),
            "deepseek": dict(_provider_circuit_state("deepseek")),
        },
        "deepseek": {
            "enabled": _env_bool("DEEPSEEK_ENABLED", True),
            "model_chat": str(os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
            "model_reasoner": str(os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")),
            "budget": deepseek_budget,
        },
    }
