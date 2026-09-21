"""Geo and ranking scoring helpers for CV recommendations."""

from __future__ import annotations

from .models import CVAnalysisResult, RecommendedJobPreview
from services.cv_analyzer import extract_skills_from_text

from .parsing_constants import INTERNATIONAL_SOURCE_NAMES, LOCAL_SOURCE_NAMES
from .parsing_geo_context import _infer_geo_preferences, _infer_role_keywords, _is_low_quality_job_title
from .parsing_core import _normalize_skill_name
from .text_utils import _fold_text

__all__ = [
    "_geo_score_adjustment",
    "_recommendation_alignment_signals",
    "_rerank_jobs_for_candidate_context",
    "_filter_meaningful_jobs",
]

_NOISY_JOB_MARKERS = (
    "cliquez pour lire",
    "chercheurs d'emploi",
    "chercheurs d emploi",
    "nos conseils en recherche",
    "formation certifiante",
    "inscription chercheurs",
    "urgent : offre de formation",
    "urgent offre de formation",
    "platon",
)


def _geo_score_adjustment(job: RecommendedJobPreview, geo: dict[str, object]) -> float:
    preferred_country = str(geo.get("preferred_country") or "").strip()
    preferred_locations = list(geo.get("preferred_locations") or [])
    remote_friendly = bool(geo.get("remote_friendly"))
    location = _fold_text(job.location)
    country = _fold_text(job.country)
    source_name = _fold_text(job.source_name)
    adjustment = 0.0
    if preferred_country == "Togo":
        if any(_fold_text(loc) in location for loc in preferred_locations):
            adjustment += 0.18
        if country == "togo" or "togo" in location:
            adjustment += 0.14
        elif source_name in LOCAL_SOURCE_NAMES and country in {"", "afrique"}:
            adjustment += 0.04
        elif "afrique" in country or source_name == "wiijob":
            adjustment -= 0.06
        elif (
            country in {"international", "allemagne", "france", "usa", "suisse", "ethiopie"}
            or any(token in location for token in ("remote", "international", "allemagne", "germany", "berlin"))
            or source_name in INTERNATIONAL_SOURCE_NAMES
        ):
            adjustment -= 0.18 if remote_friendly else 0.30
    if preferred_locations:
        if any(_fold_text(loc) in location for loc in preferred_locations):
            adjustment += 0.08
        elif location and preferred_country == "Togo" and "togo" not in location and country not in {"", "togo"}:
            adjustment -= 0.05
    if _is_low_quality_job_title(job.title):
        adjustment -= 0.25
    return adjustment


def _job_text_noise_penalty(job: RecommendedJobPreview) -> float:
    blob = _fold_text(f"{job.title or ''} {job.company or ''} {job.summary or ''}")
    penalty = 0.0
    if any(marker in blob for marker in _NOISY_JOB_MARKERS):
        penalty -= 0.18
    if len(str(job.company or "").strip()) > 90:
        penalty -= 0.08
    if len(str(job.summary or "").strip()) < 40:
        penalty -= 0.04
    return penalty


def _recommendation_alignment_signals(
    *,
    jobs: list[RecommendedJobPreview],
    cv_analysis: CVAnalysisResult,
    cv_text: str,
) -> tuple[int, int]:
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    role_keywords = _infer_role_keywords(cv_text, cv_analysis)
    overlap_jobs = 0
    role_match_jobs = 0
    for job in jobs[:3]:
        job_blob = _fold_text(f"{job.title or ''} {job.summary or ''}")
        if cv_skill_set:
            job_skills = extract_skills_from_text(f"{job.title or ''} {job.summary or ''}")
            overlap = sum(1 for skill in job_skills if _normalize_skill_name(skill) in cv_skill_set)
            if overlap > 0:
                overlap_jobs += 1
        if role_keywords and any(keyword in job_blob for keyword in role_keywords):
            role_match_jobs += 1
    return overlap_jobs, role_match_jobs


def _rerank_jobs_for_candidate_context(
    *,
    jobs: list[RecommendedJobPreview],
    cv_analysis: CVAnalysisResult,
    cv_text: str,
    explicit_location: str | None,
    top_k: int,
) -> list[RecommendedJobPreview]:
    if not jobs:
        return []
    geo = _infer_geo_preferences(cv_text, explicit_location)
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    role_keywords = _infer_role_keywords(cv_text, cv_analysis)
    rescored: list[tuple[float, int, RecommendedJobPreview]] = []
    for idx, job in enumerate(jobs):
        raw_score = float(job.score or 0.0)
        score = (raw_score * 0.58) + _geo_score_adjustment(job, geo)
        score += _job_text_noise_penalty(job)
        title_blob = _fold_text(job.title or "")
        summary_blob = _fold_text(job.summary or "")
        combined_blob = _fold_text(f"{job.title or ''} {job.summary or ''}")
        job_skills = extract_skills_from_text(f"{job.title} {job.summary}")
        overlap = 0
        if cv_skill_set:
            overlap = sum(1 for skill in job_skills if _normalize_skill_name(skill) in cv_skill_set)
            score += min(0.18, overlap * 0.045)
        if role_keywords:
            title_matches = sum(1 for keyword in role_keywords if keyword in title_blob)
            summary_matches = sum(1 for keyword in role_keywords if keyword in summary_blob)
            if title_matches:
                score += min(0.24, title_matches * 0.12)
            elif summary_matches:
                score += min(0.10, summary_matches * 0.05)
            else:
                score -= 0.34
            if title_matches == 0 and summary_matches == 0 and overlap <= 1:
                score -= 0.10
            if title_matches == 0 and cv_skill_set:
                score -= 0.04
        elif cv_skill_set and overlap == 0 and len(combined_blob) > 12:
            score -= 0.08
        rescored.append((score, idx, job))
    rescored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    reranked: list[RecommendedJobPreview] = []
    for score, _, job in rescored:
        reranked.append(job.model_copy(update={"score": round(score, 6)}))
        if len(reranked) >= top_k:
            break
    return reranked


def _filter_meaningful_jobs(
    jobs: list[RecommendedJobPreview],
    *,
    top_k: int,
) -> list[RecommendedJobPreview]:
    if not jobs:
        return []
    from .budget import _env_float

    min_score = _env_float("RECOMMENDATION_MIN_MEANINGFUL_SCORE", 0.52)
    max_negative_gap = _env_float("RECOMMENDATION_MAX_SCORE_DROP_FROM_TOP", 0.22)
    top_score = float(jobs[0].score or 0.0)
    out: list[RecommendedJobPreview] = []
    for job in jobs:
        score = float(job.score or 0.0)
        if score < min_score:
            continue
        if (top_score - score) > max_negative_gap:
            continue
        out.append(job)
        if len(out) >= top_k:
            break
    return out
