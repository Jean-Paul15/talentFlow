"""DeepSeek budget helpers and runtime state."""

from __future__ import annotations

try:  # pragma: no cover
    from core.metrics import llm_budget_ratio
except Exception:  # pragma: no cover
    llm_budget_ratio = None

from loguru import logger

from .cache import _get_llm_cache_client
from .runtime_config import _env_float, _env_int

__all__ = [
    "_deepseek_budget_keys",
    "_deepseek_budget_limits",
    "_deepseek_get_budget_state",
    "_deepseek_reasoner_max_share",
    "_deepseek_reasoner_allowed_by_share",
    "_deepseek_can_spend_more",
    "_deepseek_record_usage",
]


def _deepseek_budget_keys() -> dict[str, str]:
    from datetime import datetime, timezone

    day_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    return {
        "tokens": f"llm:budget:deepseek:tokens:{day_key}",
        "cost": f"llm:budget:deepseek:cost_usd:{day_key}",
        "calls_total": f"llm:budget:deepseek:calls_total:{day_key}",
        "calls_reasoner": f"llm:budget:deepseek:calls_reasoner:{day_key}",
    }


def _deepseek_budget_limits() -> tuple[int, float]:
    return (
        max(0, _env_int("DEEPSEEK_DAILY_TOKEN_BUDGET", 500000)),
        max(0.0, _env_float("DEEPSEEK_DAILY_COST_BUDGET_USD", 5.0)),
    )


def _deepseek_get_budget_state() -> dict[str, float]:
    client = _get_llm_cache_client()
    token_limit, cost_limit = _deepseek_budget_limits()
    if client is None:
        return {
            "tokens_used": 0.0,
            "cost_used": 0.0,
            "token_limit": float(token_limit),
            "cost_limit": float(cost_limit),
            "token_ratio": 0.0,
            "cost_ratio": 0.0,
            "calls_total": 0.0,
            "calls_reasoner": 0.0,
        }
    keys = _deepseek_budget_keys()
    try:
        tokens_used = float(client.get(keys["tokens"]) or 0)
        cost_used = float(client.get(keys["cost"]) or 0)
        calls_total = float(client.get(keys["calls_total"]) or 0)
        calls_reasoner = float(client.get(keys["calls_reasoner"]) or 0)
    except Exception:
        tokens_used = 0.0
        cost_used = 0.0
        calls_total = 0.0
        calls_reasoner = 0.0
    token_ratio = (tokens_used / token_limit) if token_limit > 0 else 0.0
    cost_ratio = (cost_used / cost_limit) if cost_limit > 0 else 0.0
    if llm_budget_ratio is not None:
        try:
            llm_budget_ratio.labels(provider="deepseek", budget_kind="tokens").set(max(0.0, token_ratio))
            llm_budget_ratio.labels(provider="deepseek", budget_kind="cost").set(max(0.0, cost_ratio))
        except Exception:
            pass
    return {
        "tokens_used": tokens_used,
        "cost_used": cost_used,
        "token_limit": float(token_limit),
        "cost_limit": float(cost_limit),
        "token_ratio": token_ratio,
        "cost_ratio": cost_ratio,
        "calls_total": calls_total,
        "calls_reasoner": calls_reasoner,
    }


def _deepseek_reasoner_max_share() -> float:
    return min(1.0, max(0.0, _env_float("DEEPSEEK_REASONER_MAX_SHARE", 0.2)))


def _deepseek_reasoner_allowed_by_share(state: dict[str, float]) -> bool:
    calls_total = float(state.get("calls_total") or 0.0)
    calls_reasoner = float(state.get("calls_reasoner") or 0.0)
    if calls_total <= 0:
        return True
    ratio = calls_reasoner / max(1.0, calls_total)
    return ratio < _deepseek_reasoner_max_share()


def _deepseek_can_spend_more() -> tuple[bool, str | None, dict[str, float]]:
    state = _deepseek_get_budget_state()
    if state["token_limit"] > 0 and state["tokens_used"] >= state["token_limit"]:
        return False, "deepseek_token_budget_exceeded", state
    if state["cost_limit"] > 0 and state["cost_used"] >= state["cost_limit"]:
        return False, "deepseek_cost_budget_exceeded", state
    return True, None, state


def _deepseek_record_usage(*, model: str, prompt_tokens: int, completion_tokens: int, estimated_cost_usd: float) -> None:
    client = _get_llm_cache_client()
    if client is None:
        return
    keys = _deepseek_budget_keys()
    ttl = 48 * 3600
    try:
        pipe = client.pipeline()
        pipe.incrby(keys["tokens"], int(max(0, prompt_tokens) + max(0, completion_tokens)))
        pipe.incrbyfloat(keys["cost"], float(max(0.0, estimated_cost_usd)))
        pipe.incrby(keys["calls_total"], 1)
        if "reasoner" in str(model or "").lower():
            pipe.incrby(keys["calls_reasoner"], 1)
        pipe.expire(keys["tokens"], ttl)
        pipe.expire(keys["cost"], ttl)
        pipe.expire(keys["calls_total"], ttl)
        pipe.expire(keys["calls_reasoner"], ttl)
        pipe.execute()
    except Exception as err:
        logger.debug(f"DeepSeek budget usage record ignore: {err}")
