"""Fallback assistant payload construction."""

from __future__ import annotations

from .models import CVAnalysisResult, RecommendedJobPreview

from .parsing_assistant_defaults import _default_actions, _default_gaps, _default_profile_summary, _default_strengths
from .parsing_core import (
    _build_default_offer_playbook,
    _build_default_score_explanation,
    _fallback_job_why,
    _no_match_reason,
    _suggest_cv_improvement_for_job,
)
from .text_utils import _canonicalize_url

__all__ = ["_build_fallback_assistant_structured"]


def _build_fallback_assistant_structured(
    *,
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    mode: str,
    decision_reason: str,
    output_language: str = "fr",
) -> dict:
    profile_summary = _default_profile_summary(cv_analysis)
    strengths = _default_strengths(cv_analysis)
    gaps = _default_gaps(cv_analysis, jobs)
    actions = _default_actions(cv_analysis, jobs)
    if mode == "no_match":
        return {
            "mode": "no_match",
            "profile_summary": profile_summary,
            "strengths": strengths[:3],
            "gaps": gaps[:3],
            "recommended_jobs": [],
            "score_explanation": _build_default_score_explanation(
                overall_score=52,
                structure_score=58,
                alignment_score=48,
                evidence_score=50,
                language=output_language,
            ),
            "offer_playbooks": [],
            "actions": actions[:3],
            "reason_if_no_match": _no_match_reason(decision_reason),
        }
    recommended_jobs = []
    offer_playbooks = []
    for job in jobs[:3]:
        recommended_jobs.append(
            {
                "job_id": job.id,
                "title": job.title,
                "why": _fallback_job_why(cv_analysis, job),
                "url": _canonicalize_url(job.source_url),
                "cv_improvement": _suggest_cv_improvement_for_job(cv_analysis, job),
            }
        )
        offer_playbooks.append(
            _build_default_offer_playbook(
                cv_analysis=cv_analysis,
                job=job,
                language=output_language,
            )
        )
    return {
        "mode": "match",
        "profile_summary": profile_summary,
        "strengths": strengths[:3],
        "gaps": gaps[:3],
        "recommended_jobs": recommended_jobs,
        "score_explanation": _build_default_score_explanation(
            overall_score=64,
            structure_score=68,
            alignment_score=62,
            evidence_score=58,
            language=output_language,
        ),
        "offer_playbooks": offer_playbooks[:3],
        "actions": actions[:3],
        "reason_if_no_match": None,
    }
