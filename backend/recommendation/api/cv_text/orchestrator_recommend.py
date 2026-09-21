"""Recommendation assistant helpers for CV text recommendation flows."""

from __future__ import annotations

import os

from .cache import _cache_get_json, _cache_set_json, _build_reco_repair_cache_key
from .runtime_config import _env_bool, _env_int
from .models import CVAnalysisResult, RecommendedJobPreview
from .parsing import (
    _build_recommendation_messages,
    _build_recommendation_prompt,
    _coerce_assistant_structured,
    _recommendation_structured_schema,
)
from .providers import _generate_final_response
from .recommendation_calibration import _should_force_deepseek_first

__all__ = ["_generate_recommendation_assistant"]


async def _generate_recommendation_assistant(
    *,
    cv_text: str,
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    expected_mode: str,
    decision_reason: str,
    output_language: str,
    explicit_model: str | None,
    client_ip: str,
) -> tuple[dict | None, str | None, str | None, str | None, str | None]:
    schema = _recommendation_structured_schema()
    repair_key = _build_reco_repair_cache_key(
        cv_text=cv_text,
        expected_mode=expected_mode,
        jobs=jobs,
    )
    repair_seed = _cache_get_json(repair_key) or {}
    force_retry_hint = bool(repair_seed.get("quality_gate_failed"))
    status_hint = None
    force_deepseek_first = (
        not explicit_model
        and _env_bool("DEEPSEEK_ENABLED", True)
        and _should_force_deepseek_first(
            jobs=jobs,
            expected_mode=expected_mode,
            decision_reason=decision_reason,
        )
    )
    for attempt in range(2):
        effective_model = explicit_model
        if attempt == 0 and force_deepseek_first:
            deepseek_model = str(os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip() or "deepseek-chat"
            effective_model = f"deepseek:{deepseek_model}"
        elif attempt > 0 and not explicit_model:
            deepseek_model = str(os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip() or "deepseek-chat"
            effective_model = f"deepseek:{deepseek_model}"
        prompt = _build_recommendation_prompt(
            cv_analysis,
            jobs,
            expected_mode=expected_mode,
            decision_reason=decision_reason,
            output_language=output_language,
            retry_hint=(attempt > 0 or force_retry_hint),
        )
        messages = _build_recommendation_messages(
            cv_analysis,
            jobs,
            expected_mode=expected_mode,
            decision_reason=decision_reason,
            output_language=output_language,
            retry_hint=(attempt > 0 or force_retry_hint),
        )
        text, provider, used_model, error, status_hint = await _generate_final_response(
            prompt,
            explicit_model=effective_model,
            structured_schema=schema,
            expected_mode=expected_mode,
            attempt=attempt,
            client_ip=client_ip,
            prompt_messages=messages,
        )
        if not text:
            return None, provider, used_model, error, status_hint
        payload = _coerce_assistant_structured(
            text,
            jobs=jobs,
            cv_analysis=cv_analysis,
            expected_mode=expected_mode,
            output_language=output_language,
        )
        if payload:
            return payload, provider, used_model, None, None
        error = "quality_gate_rejected"
        _cache_set_json(
            repair_key,
            {"quality_gate_failed": True, "attempt": attempt + 1},
            ttl_seconds=_env_int("LLM_REPAIR_CACHE_TTL_SECONDS", 300),
        )
    return None, None, None, "quality_gate_rejected", status_hint
