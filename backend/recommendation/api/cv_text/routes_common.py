"""Shared route helpers for CV text endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.cv_analyzer import (
    extract_education_level,
    extract_experience_years,
    extract_skills_from_text,
)

from .models import CVAnalysisResult, RecommendedJobPreview
from .parsing import _clean_text, _safe_float, _summarize_job

__all__ = [
    "router",
    "_ensure_cv_text",
    "_build_cv_analysis",
    "_build_recommended_job_previews",
]

router = APIRouter(prefix="/cv", tags=["cv"])


def _ensure_cv_text(cv_text: str) -> str:
    text = str(cv_text or "").strip()
    if len(text) < 10:
        raise HTTPException(400, "CV trop court")
    return text


def _build_cv_analysis(cv_text: str) -> CVAnalysisResult:
    skills = extract_skills_from_text(cv_text)
    experience_years = extract_experience_years(cv_text)
    education_level = extract_education_level(cv_text)
    preview = cv_text[:200].replace("\n", " ")
    return CVAnalysisResult(
        skills=skills,
        experience_years=experience_years,
        education_level=education_level,
        raw_text_preview=preview,
    )


def _build_recommended_job_previews(raw_results: list[dict]) -> list[RecommendedJobPreview]:
    jobs: list[RecommendedJobPreview] = []
    for row in raw_results:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        jobs.append(
            RecommendedJobPreview(
                id=str(row.get("id") or ""),
                title=title,
                company=_clean_text(row.get("company")),
                location=_clean_text(row.get("location")),
                country=_clean_text(row.get("country")),
                contract_type=_clean_text(row.get("contract_type")),
                source_name=_clean_text(row.get("source_name")),
                source_url=_clean_text(row.get("source_url")),
                posted_date=_clean_text(row.get("posted_date")),
                score=_safe_float(row.get("score")),
                summary=_summarize_job(row),
            )
        )
    return jobs
