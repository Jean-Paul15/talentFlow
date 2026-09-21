"""Decision helpers for recommendation response mode selection."""

from __future__ import annotations

from .budget import _env_float, _env_int
from .models import CVAnalysisResult, RecommendedJobPreview

from .parsing_geo import _recommendation_alignment_signals

__all__ = ["_recommendation_response_mode"]


def _recommendation_response_mode(
    jobs: list[RecommendedJobPreview],
    cv_analysis: CVAnalysisResult,
    cv_text: str,
) -> tuple[str, str]:
    if not jobs:
        return "no_match", "no_meaningful_jobs"
    min_job_count = _env_int("LLM_DECISION_MIN_JOB_COUNT", 2)
    min_top_score = _env_float("LLM_DECISION_MIN_TOP_SCORE", 0.62)
    min_score_gap = _env_float("LLM_DECISION_MIN_SCORE_GAP", 0.04)
    min_meaningful_score = _env_float("RECOMMENDATION_MIN_MEANINGFUL_SCORE", 0.52)
    single_strong_match_score = _env_float(
        "RECOMMENDATION_SINGLE_STRONG_MATCH_SCORE",
        max(min_meaningful_score + 0.22, min_top_score + 0.20),
    )
    scores = [float(j.score) for j in jobs if j.score is not None]
    if not scores:
        return "no_match", "missing_scores"
    top_score = scores[0]
    second_score = scores[1] if len(scores) > 1 else 0.0
    meaningful_count = sum(1 for score in scores[:5] if score >= min_meaningful_score)
    overlap_jobs, role_match_jobs = _recommendation_alignment_signals(jobs=jobs, cv_analysis=cv_analysis, cv_text=cv_text)
    if top_score < min_top_score:
        return "no_match", "low_confidence_top_score"
    if (
        meaningful_count == 1
        and top_score >= single_strong_match_score
    ):
        return "match", "strong_single_match"
    if (
        meaningful_count >= 1
        and (top_score - second_score) < min_score_gap
        and overlap_jobs == 0
        and role_match_jobs == 0
    ):
        return "no_match", "tight_score_gap"
    if meaningful_count < max(1, min_job_count):
        return "no_match", "too_few_meaningful_jobs"
    if overlap_jobs == 0 and role_match_jobs == 0:
        return "no_match", "low_skill_role_alignment"
    return "match", "high_confidence_jobs"
