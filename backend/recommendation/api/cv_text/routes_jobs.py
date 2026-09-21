"""Recommendation core for CV text routes."""

from __future__ import annotations

from fastapi import HTTPException, Request

try:  # pragma: no cover
    from core.metrics import llm_cache_hit_total, llm_cache_miss_total
except Exception:  # pragma: no cover
    llm_cache_hit_total = None
    llm_cache_miss_total = None

from .budget import _client_ip, _env_bool, _env_int, _rate_guard_allow
from .cache import _build_reco_llm_cache_key, _cache_get_json, _cache_set_json
from .cv_document_classifier import ensure_cv_document_or_raise
from .models import (
    AtsLitePayload,
    AssistantStructuredPayload,
    CVRecommendTextRequest,
    CVRecommendTextResponse,
)
from .orchestrator import _generate_recommendation_assistant
from .parsing import (
    _build_ats_lite_payload,
    _build_default_score_explanation,
    _build_fallback_assistant_structured,
    _coerce_assistant_structured,
    _detect_cv_language,
    _llm_status_from_error,
    _recommendation_response_mode,
    _render_assistant_structured,
)
from .prompt_safety import assess_prompt_injection_risk
from .routes_common import _build_cv_analysis, _ensure_cv_text
from .routes_recommend_search import _prepare_recommendation_search_context

__all__ = ["_recommend_from_cv_text_core"]


async def _recommend_from_cv_text_core(
    request: CVRecommendTextRequest,
    request_obj: Request,
) -> CVRecommendTextResponse:
    cv_text = _ensure_cv_text(request.cv_text)
    prompt_safety = assess_prompt_injection_risk(cv_text)
    if prompt_safety.blocked:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PROMPT_INJECTION_BLOCKED",
                "message": (
                    "Le document contient des instructions non pertinentes pour un CV. "
                    "Supprime ces instructions puis relance l'analyse."
                ),
                "riskScore": prompt_safety.risk_score,
            },
        )
    cv_text_safe = prompt_safety.sanitized_text or cv_text
    output_language = _detect_cv_language(cv_text_safe)

    if not _rate_guard_allow(
        scope="recommend",
        limit=max(1, _env_int("RATE_LIMIT_LLM", 30)),
        key_suffix=_client_ip(request_obj),
    ):
        raise HTTPException(429, "Trop de requêtes recommandation, réessaie dans 1 minute.")

    cv_analysis = _build_cv_analysis(cv_text_safe)
    force_llm_final = _env_bool("LLM_FORCE_FINAL_DECISION", True)
    use_llm = bool(request.use_llm) or force_llm_final
    await ensure_cv_document_or_raise(
        cv_text_safe,
        cv_analysis=cv_analysis,
        use_llm=use_llm,
        client_ip=_client_ip(request_obj),
    )
    query_text, jobs = await _prepare_recommendation_search_context(
        request,
        cv_analysis,
        cv_text_safe,
    )

    llm_used = False
    llm_error = None
    llm_model = None
    llm_provider = None
    response_mode, decision_reason = _recommendation_response_mode(jobs, cv_analysis, cv_text_safe)
    assistant_structured = _build_fallback_assistant_structured(
        cv_analysis=cv_analysis,
        jobs=jobs,
        mode=response_mode,
        decision_reason=decision_reason,
        output_language=output_language,
    )
    assistant_message = _render_assistant_structured(assistant_structured)
    llm_status = "fallback_used"

    if use_llm:
        cache_key = _build_reco_llm_cache_key(
            cv_text=cv_text_safe,
            query_used=query_text,
            request=request,
            jobs=jobs,
            expected_mode=response_mode,
        )
        cached = _cache_get_json(cache_key)
        cached_payload = _coerce_assistant_structured(
            (cached or {}).get("assistant_structured"),
            jobs=jobs,
            cv_analysis=cv_analysis,
            expected_mode=response_mode,
            output_language=output_language,
        )
        if cached_payload:
            assistant_structured = cached_payload
            assistant_message = _render_assistant_structured(cached_payload)
            llm_used = True
            llm_provider = str((cached or {}).get("llm_provider") or "gemini")
            llm_model = str((cached or {}).get("llm_model") or "gemini-2.5-flash-lite")
            llm_status = "used_cached"
            if llm_cache_hit_total is not None:
                llm_cache_hit_total.labels(provider=llm_provider or "unknown").inc()
        else:
            if llm_cache_miss_total is not None:
                llm_cache_miss_total.labels(provider="all").inc()
            llm_payload, llm_provider, llm_model, llm_error, llm_status_hint = await _generate_recommendation_assistant(
                cv_text=cv_text_safe,
                cv_analysis=cv_analysis,
                jobs=jobs,
                expected_mode=response_mode,
                decision_reason=decision_reason,
                output_language=output_language,
                explicit_model=request.llm_model,
                client_ip=_client_ip(request_obj),
            )
            if llm_payload:
                assistant_structured = llm_payload
                assistant_message = _render_assistant_structured(llm_payload)
                llm_used = True
                llm_status = "used"
                ttl = _env_int("LLM_CACHE_TTL_SECONDS", 24 * 3600)
                _cache_set_json(
                    cache_key,
                    {
                        "assistant_message": assistant_message,
                        "assistant_structured": assistant_structured,
                        "llm_provider": llm_provider,
                        "llm_model": llm_model,
                    },
                    ttl_seconds=ttl,
                )
            else:
                llm_status = llm_status_hint or _llm_status_from_error(llm_error)

    if response_mode == "no_match" and not llm_used and llm_status == "fallback_used":
        llm_status = "no_match"

    ats_lite = _build_ats_lite_payload(
        cv_text=cv_text_safe,
        cv_analysis=cv_analysis,
        jobs=jobs,
        assistant_structured=assistant_structured,
    )
    if not str(assistant_structured.get("score_explanation") or "").strip():
        assistant_structured["score_explanation"] = _build_default_score_explanation(
            overall_score=int(ats_lite.get("overall_score") or 0),
            structure_score=int(ats_lite.get("structure_score") or 0),
            alignment_score=int(ats_lite.get("alignment_score") or 0),
            evidence_score=int(ats_lite.get("evidence_score") or 0),
            language=output_language,
        )

    return CVRecommendTextResponse(
        cv_analysis=cv_analysis,
        query_used=query_text,
        total_results=len(jobs),
        jobs=jobs,
        assistant_message=assistant_message,
        llm_used=llm_used,
        llm_provider=(llm_provider if llm_used else None),
        llm_model=(llm_model if llm_used else None),
        llm_error=llm_error,
        llm_status=llm_status,
        assistant_structured=AssistantStructuredPayload.model_validate(assistant_structured),
        ats_lite=AtsLitePayload.model_validate(ats_lite),
    )
