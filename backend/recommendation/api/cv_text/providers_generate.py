"""Final provider orchestration for CV text recommendation flows."""

from __future__ import annotations

import os

from .budget import (
    _acquire_llm_queue_slot,
    _deepseek_can_spend_more,
    _deepseek_rate_limit_allow,
    _deepseek_record_usage,
    _env_bool,
    _provider_circuit_can_attempt,
    _provider_circuit_record_failure,
    _provider_circuit_record_success,
    _provider_order,
    _release_llm_queue_slot,
)
from .providers_deepseek import _generate_with_deepseek
from .providers_gemini import _generate_with_gemini
from .providers_select import _pick_deepseek_model, _resolve_explicit_provider, _resolve_provider_explicit_model

try:  # pragma: no cover
    from core.metrics import llm_fallback_total
except Exception:  # pragma: no cover
    llm_fallback_total = None

__all__ = ["_generate_final_response"]


async def _generate_final_response(
    prompt: str,
    explicit_model: str | None = None,
    structured_schema: dict | None = None,
    *,
    expected_mode: str | None = None,
    attempt: int = 0,
    client_ip: str = "unknown",
    prompt_messages: list[dict[str, str]] | None = None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """
    Orchestrateur de génération finale:
    - Gemini en premier
    - DeepSeek en fallback provider
    - puis fallback déterministe côté moteur appelant
    """
    errors: list[str] = []
    status_hint: str | None = None
    provider_order = _provider_order()
    forced_provider = _resolve_explicit_provider(explicit_model)
    for provider in provider_order:
        if forced_provider and provider != forced_provider:
            continue
        if provider == "gemini":
            if not _provider_circuit_can_attempt("gemini"):
                errors.append("gemini=circuit_open")
                continue
            gemini_model = (
                _resolve_provider_explicit_model(explicit_model, provider="gemini")
                or os.getenv("GEMINI_MODEL")
                or "gemini-2.5-flash"
            )
            text, used_model, err = await _generate_with_gemini(
                prompt,
                model=gemini_model,
                structured_schema=structured_schema,
            )
            if text:
                _provider_circuit_record_success("gemini")
                return text, "gemini", (used_model or gemini_model), None, None
            _provider_circuit_record_failure("gemini")
            errors.append(f"gemini={err or 'unavailable'}")
            continue

        if provider == "deepseek" and _env_bool("DEEPSEEK_ENABLED", True):
            if not _provider_circuit_can_attempt("deepseek"):
                errors.append("deepseek=circuit_open")
                continue

            allowed, rate_reason = _deepseek_rate_limit_allow(client_ip)
            if not allowed:
                status_hint = "rate_limited_fallback"
                errors.append(f"deepseek={rate_reason}")
                if llm_fallback_total is not None:
                    llm_fallback_total.labels(reason="rate_limited").inc()
                continue

            can_spend, budget_reason, budget_state = _deepseek_can_spend_more()
            if not can_spend:
                status_hint = "fallback_used"
                errors.append(f"deepseek={budget_reason}")
                if llm_fallback_total is not None:
                    llm_fallback_total.labels(reason="budget_guard").inc()
                continue

            deepseek_model = _pick_deepseek_model(
                prompt=prompt,
                explicit_model=explicit_model,
                expected_mode=expected_mode,
                attempt=attempt,
                budget_state=budget_state,
            )
            got_slot, queue_reason = await _acquire_llm_queue_slot("deepseek")
            if not got_slot:
                status_hint = "queue_timeout_fallback"
                errors.append(f"deepseek={queue_reason}")
                if llm_fallback_total is not None:
                    llm_fallback_total.labels(reason="queue_timeout").inc()
                continue
            try:
                deepseek_text, deepseek_used_model, deepseek_err, usage = await _generate_with_deepseek(
                    prompt,
                    model=deepseek_model,
                    structured_schema=structured_schema,
                    messages=prompt_messages,
                )
            finally:
                await _release_llm_queue_slot("deepseek")
            if deepseek_text:
                _provider_circuit_record_success("deepseek")
                if usage:
                    _deepseek_record_usage(
                        model=(deepseek_used_model or deepseek_model),
                        prompt_tokens=int(usage.get("prompt_tokens") or 0),
                        completion_tokens=int(usage.get("completion_tokens") or 0),
                        estimated_cost_usd=float(usage.get("estimated_cost_usd") or 0.0),
                    )
                return (
                    deepseek_text,
                    "deepseek",
                    (deepseek_used_model or deepseek_model),
                    None,
                    None,
                )
            _provider_circuit_record_failure("deepseek")
            errors.append(f"deepseek={deepseek_err or 'unavailable'}")
            continue

    error = " | ".join(errors) if errors else "Aucun provider disponible"
    return None, None, None, error, status_hint
