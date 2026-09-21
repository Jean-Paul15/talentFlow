"""Offer improvement core for CV text routes."""

from __future__ import annotations

from fastapi import HTTPException

from services.cv_analyzer import extract_skills_from_text

from .budget import _env_bool, _env_int
from .cache import _build_offer_llm_cache_key, _cache_get_json, _cache_set_json
from .cv_document_classifier import ensure_cv_document_or_raise
from .models import CVImproveForOfferRequest, CVImproveForOfferResponse
from .providers import _generate_final_response
from .parsing import (
    _build_offer_improvement_prompt,
    _detect_cv_language,
    _deterministic_offer_improvements,
    _is_improvement_response_usable,
    _llm_decision_for_offer_improvement,
    _parse_improvement_bullets,
)
from .prompt_safety import assess_prompt_injection_risk
from .routes_common import _build_cv_analysis, _ensure_cv_text

__all__ = ["_improve_cv_for_offer_core"]


async def _improve_cv_for_offer_core(request: CVImproveForOfferRequest) -> CVImproveForOfferResponse:
    cv_text = _ensure_cv_text(request.cv_text)
    prompt_safety = assess_prompt_injection_risk(cv_text)
    if prompt_safety.blocked:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PROMPT_INJECTION_BLOCKED",
                "message": (
                    "Le document contient des instructions non pertinentes pour un CV. "
                    "Supprime ces instructions puis renvoie un CV propre."
                ),
                "riskScore": prompt_safety.risk_score,
            },
        )
    cv_text_safe = prompt_safety.sanitized_text or cv_text
    cv_analysis = _build_cv_analysis(cv_text_safe)
    output_language = _detect_cv_language(cv_text_safe)
    force_llm_final = _env_bool("LLM_FORCE_FINAL_DECISION", True)
    use_llm = bool(request.use_llm) or force_llm_final
    await ensure_cv_document_or_raise(
        cv_text_safe,
        cv_analysis=cv_analysis,
        use_llm=use_llm,
        client_ip="internal",
    )

    job_text = f"{request.job_title} {request.job_summary}".strip()
    job_skills = extract_skills_from_text(job_text)
    cv_skill_set = {s.lower() for s in cv_analysis.skills}
    missing_skills = [s for s in job_skills if s.lower() not in cv_skill_set][:8]

    improvements = _deterministic_offer_improvements(
        cv_analysis=cv_analysis,
        job_title=request.job_title,
        job_summary=request.job_summary,
        missing_skills=missing_skills,
    )

    llm_used = False
    llm_provider = None
    llm_model = None
    llm_error = None

    if use_llm:
        should_call_llm, decision_reason = _llm_decision_for_offer_improvement(
            cv_analysis=cv_analysis,
            job_title=request.job_title,
            job_summary=request.job_summary,
            missing_skills=missing_skills,
        )
        if should_call_llm:
            cache_key = _build_offer_llm_cache_key(
                cv_text=cv_text_safe,
                request=request,
                missing_skills=missing_skills,
            )
            cached = _cache_get_json(cache_key)
            cached_improvements = (cached or {}).get("improvements")
            if isinstance(cached_improvements, list) and _is_improvement_response_usable(cached_improvements):
                improvements = [str(x) for x in cached_improvements]
                llm_used = True
                llm_provider = "cache"
                llm_model = str((cached or {}).get("llm_model") or "cached")
            else:
                llm_prompt = _build_offer_improvement_prompt(
                    cv_analysis=cv_analysis,
                    job_title=request.job_title,
                    job_summary=request.job_summary,
                    job_url=request.job_url,
                    missing_skills=missing_skills,
                    deterministic_improvements=improvements,
                    output_language=output_language,
                )
                llm_text, llm_provider, llm_model, llm_error, _status_hint = await _generate_final_response(
                    llm_prompt,
                    explicit_model=request.llm_model,
                    client_ip="internal",
                )
                if llm_text:
                    parsed = _parse_improvement_bullets(llm_text)
                    if parsed and _is_improvement_response_usable(parsed):
                        improvements = parsed
                        llm_used = True
                        ttl = _env_int("LLM_CACHE_TTL_SECONDS", 24 * 3600)
                        _cache_set_json(
                            cache_key,
                            {
                                "improvements": improvements,
                                "llm_provider": llm_provider,
                                "llm_model": llm_model,
                            },
                            ttl_seconds=ttl,
                        )
                    elif parsed and not _is_improvement_response_usable(parsed):
                        llm_error = (
                            f"{llm_error} | quality_gate_rejected"
                            if llm_error
                            else "quality_gate_rejected"
                        )
        else:
            llm_error = f"llm_skipped:{decision_reason}"

    return CVImproveForOfferResponse(
        cv_analysis=cv_analysis,
        job_title=request.job_title,
        job_url=request.job_url,
        missing_skills=missing_skills,
        improvements=improvements,
        llm_used=llm_used,
        llm_provider=llm_provider if llm_used else None,
        llm_model=llm_model if llm_used else None,
        llm_error=llm_error,
    )
