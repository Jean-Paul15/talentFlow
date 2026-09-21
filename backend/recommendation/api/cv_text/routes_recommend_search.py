"""Recommendation search preparation for CV text routes."""

from __future__ import annotations

from fastapi import Request
from services.embedding_service import get_embedding_service

from .models import CVAnalysisResult, CVRecommendTextRequest, RecommendedJobPreview
from .orchestrator import _search_jobs
from .parsing import (
    _build_search_query,
    _filter_meaningful_jobs,
    _normalize_search_location_filter,
    _recommendation_alignment_signals,
    _rerank_jobs_for_candidate_context,
)
from .recommendation_calibration import (
    _build_fallback_query_from_skills,
    _build_precision_query_from_profile,
    _should_retry_with_precision_query,
)
from .routes_common import _build_recommended_job_previews

__all__ = ["_prepare_recommendation_search_context"]


async def _prepare_recommendation_search_context(
    request: CVRecommendTextRequest,
    cv_analysis: CVAnalysisResult,
    cv_text: str,
) -> tuple[str, list[RecommendedJobPreview]]:
    skills = cv_analysis.skills
    experience_years = cv_analysis.experience_years
    education_level = cv_analysis.education_level
    fallback_query = _build_fallback_query_from_skills(
        skills=skills,
        experience_years=experience_years,
    )
    precision_query = _build_precision_query_from_profile(
        cv_text=cv_text,
        skills=skills,
        experience_years=experience_years,
    )

    query_text = _build_search_query(
        cv_text=cv_text,
        skills=skills,
        experience_years=experience_years,
        education_level=education_level,
    )
    normalized_location_filter = _normalize_search_location_filter(request.location)
    search_limit = min(max(request.top_k * 6, 20), 50)

    async def _run_search(candidate_query: str) -> list[RecommendedJobPreview]:
        payload = {
            "query": candidate_query,
            "limit": search_limit,
            "rerank": request.rerank,
            "candidate_pool_size": request.candidate_pool_size or search_limit,
            "location": normalized_location_filter,
            "contract_type": request.contract_type,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        query_vector = get_embedding_service().embed_single(candidate_query)
        search_data = await _search_jobs(payload, query_vector=query_vector)
        rows = _build_recommended_job_previews(search_data.get("results", []) or [])
        rows = _rerank_jobs_for_candidate_context(
            jobs=rows,
            cv_analysis=cv_analysis,
            cv_text=cv_text,
            explicit_location=request.location,
            top_k=request.top_k,
        )
        return _filter_meaningful_jobs(rows, top_k=request.top_k)

    jobs = await _run_search(query_text)
    overlap_jobs, role_match_jobs = _recommendation_alignment_signals(
        jobs=jobs,
        cv_analysis=cv_analysis,
        cv_text=cv_text,
    )
    if (
        precision_query
        and precision_query.strip()
        and precision_query.strip() != query_text.strip()
        and _should_retry_with_precision_query(
            jobs=jobs,
            role_match_jobs=role_match_jobs,
            overlap_jobs=overlap_jobs,
        )
    ):
        precise_jobs = await _run_search(precision_query)
        if precise_jobs:
            precise_overlap, precise_role_match = _recommendation_alignment_signals(
                jobs=precise_jobs,
                cv_analysis=cv_analysis,
                cv_text=cv_text,
            )
            if (
                precise_role_match > role_match_jobs
                or precise_overlap > overlap_jobs
                or float(precise_jobs[0].score or 0.0) >= float(jobs[0].score or 0.0)
            ):
                jobs = precise_jobs
                query_text = precision_query
                overlap_jobs, role_match_jobs = precise_overlap, precise_role_match

    if not jobs and fallback_query and fallback_query != query_text.strip():
        jobs = await _run_search(fallback_query)
        if jobs:
            query_text = fallback_query

    return query_text, jobs
