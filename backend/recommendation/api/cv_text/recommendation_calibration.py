"""Calibration helpers for recommendation search and LLM escalation."""

from __future__ import annotations

import re

from .models import RecommendedJobPreview
from .runtime_config import _env_bool, _env_float
from .text_utils import _fold_text

__all__ = [
    "_build_fallback_query_from_skills",
    "_build_precision_query_from_profile",
    "_should_force_deepseek_first",
    "_should_retry_with_precision_query",
]


_ROLE_HINTS_BY_SKILL = (
    ({"python", "fastapi", "django", "flask"}, ["developpeur python", "backend", "api"]),
    ({"react", "typescript", "javascript", "angular", "vue"}, ["developpeur frontend", "react", "typescript"]),
    ({"node.js", "node", "nestjs", "express"}, ["backend node", "full stack", "typescript"]),
    ({"machine learning", "ml", "nlp", "llm", "deep learning"}, ["ingenieur ia", "machine learning", "nlp"]),
    ({"spark", "kafka", "airflow", "etl", "data pipeline"}, ["ingenieur data", "data engineering", "etl"]),
    ({"sql", "power bi", "tableau", "excel"}, ["data analyst", "sql", "bi"]),
    ({"docker", "kubernetes", "terraform", "devops", "ci/cd"}, ["devops", "cloud", "infrastructure"]),
    ({"php", "laravel"}, ["developpeur php", "full stack", "web"]),
    ({"java", "spring", "spring boot"}, ["developpeur java", "backend", "spring"]),
)


_NOISE_MARKERS = (
    "cliquez pour lire",
    "chercheurs d'emploi",
    "chercheurs d emploi",
    "nos conseils en recherche",
    "formation certifiante",
    "inscription chercheurs",
    "urgent : offre de formation",
    "platon",
)


def _build_fallback_query_from_skills(
    *,
    skills: list[str],
    experience_years: int | None,
) -> str:
    tokens = [str(skill).strip() for skill in skills[:5] if str(skill).strip()]
    if experience_years is not None:
        tokens.append(f"{experience_years} ans")
    return " ".join(tokens).strip()


def _build_precision_query_from_profile(
    *,
    cv_text: str,
    skills: list[str],
    experience_years: int | None,
) -> str:
    folded_skills = {_fold_text(skill) for skill in skills if str(skill).strip()}
    role_tokens_out: list[str] = []
    skill_tokens: list[str] = []

    headline = re.split(r"[\n\r\.\|\-]", str(cv_text or ""), maxsplit=1)[0].strip()
    headline_folded = _fold_text(headline)

    for required_skills, inferred_tokens in _ROLE_HINTS_BY_SKILL:
        if folded_skills.intersection(required_skills) or any(token in headline_folded for token in inferred_tokens):
            for token in inferred_tokens:
                if token not in role_tokens_out:
                    role_tokens_out.append(token)

    for skill in skills[:6]:
        cleaned = str(skill).strip()
        if cleaned and cleaned.lower() not in {token.lower() for token in skill_tokens}:
            skill_tokens.append(cleaned)

    tokens = role_tokens_out[:4] + skill_tokens[:4]
    if experience_years is not None:
        tokens.append(f"{experience_years} ans")

    return " ".join(tokens[:9]).strip()


def _should_retry_with_precision_query(
    *,
    jobs: list[RecommendedJobPreview],
    role_match_jobs: int,
    overlap_jobs: int,
) -> bool:
    if not jobs:
        return True

    top_score = float(jobs[0].score or 0.0)
    noisy_top_jobs = 0
    for job in jobs[:3]:
        blob = _fold_text(f"{job.title or ''} {job.company or ''} {job.summary or ''}")
        if any(marker in blob for marker in _NOISE_MARKERS):
            noisy_top_jobs += 1

    if top_score < max(0.60, _env_float("LLM_DECISION_MIN_TOP_SCORE", 0.62) + 0.02):
        return True
    if role_match_jobs == 0:
        return True
    if overlap_jobs == 0 and top_score < 0.74:
        return True
    return noisy_top_jobs >= 2


def _should_force_deepseek_first(
    *,
    jobs: list[RecommendedJobPreview],
    expected_mode: str,
    decision_reason: str,
) -> bool:
    if not _env_bool("RECOMMENDATION_DEEPSEEK_AMBIGUOUS_FIRST_ENABLED", True):
        return False
    if not jobs:
        return False

    top_score = float(jobs[0].score or 0.0)
    min_top_score = _env_float("LLM_DECISION_MIN_TOP_SCORE", 0.62)
    borderline_delta = max(
        0.01,
        _env_float("RECOMMENDATION_DEEPSEEK_BORDERLINE_DELTA", 0.06),
    )

    if decision_reason == "strong_single_match":
        return True

    if decision_reason in {"too_few_meaningful_jobs", "low_skill_role_alignment"}:
        return top_score >= (min_top_score - borderline_delta)

    if expected_mode == "match" and top_score < (min_top_score + borderline_delta):
        return True

    if expected_mode == "no_match" and top_score >= (min_top_score - borderline_delta / 2):
        return True

    return False
