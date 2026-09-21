"""Geo context inference helpers for CV recommendations."""

from __future__ import annotations

import re

from .models import CVAnalysisResult

from .parsing_constants import LOW_QUALITY_JOB_TITLES, TOGO_LOCATION_HINTS
from .text_utils import _fold_text

__all__ = [
    "_infer_geo_preferences",
    "_normalize_search_location_filter",
    "_infer_role_keywords",
    "_is_low_quality_job_title",
]


def _infer_geo_preferences(cv_text: str, explicit_location: str | None) -> dict[str, object]:
    blob = f"{explicit_location or ''} {cv_text or ''}"
    folded = _fold_text(blob)
    preferred_locations: list[str] = []
    for key, normalized in TOGO_LOCATION_HINTS.items():
        if key in folded and normalized not in preferred_locations:
            preferred_locations.append(normalized)
    preferred_country: str | None = None
    if "togo" in folded or preferred_locations:
        preferred_country = "Togo"
    elif "senegal" in folded or "dakar" in folded:
        preferred_country = "Senegal"
    elif "cote d'ivoire" in folded or "cote d ivoire" in folded or "abidjan" in folded:
        preferred_country = "Cote d'Ivoire"
    remote_friendly = any(token in folded for token in ("remote", "teletravail", "télétravail", "hybride", "hybrid"))
    return {"preferred_country": preferred_country, "preferred_locations": preferred_locations, "remote_friendly": remote_friendly}


def _normalize_search_location_filter(location: str | None) -> str | None:
    raw = re.sub(r"\s+", " ", str(location or "")).strip()
    if not raw:
        return None
    folded = _fold_text(raw)
    for key, normalized in TOGO_LOCATION_HINTS.items():
        if key in folded:
            return normalized
    if "dakar" in folded:
        return "Dakar"
    if "abidjan" in folded:
        return "Abidjan"
    if "yaounde" in folded:
        return "Yaounde"
    if "togo" in folded and "," not in raw:
        return "Togo"
    first_token = re.split(r"[,;/|]", raw, maxsplit=1)[0].strip()
    return first_token if 2 <= len(first_token) <= 40 else None


def _infer_role_keywords(cv_text: str, cv_analysis: CVAnalysisResult) -> list[str]:
    folded = _fold_text(f"{cv_text or ''} {cv_analysis.raw_text_preview or ''}")
    ordered_keywords = [
        "assistant comptable",
        "comptable",
        "paie",
        "developpeur",
        "developpeur python",
        "developpeur java",
        "backend",
        "api",
        "frontend",
        "full stack",
        "react",
        "typescript",
        "javascript",
        "node",
        "python",
        "data engineer",
        "ingenieur data",
        "data scientist",
        "ingenieur ia",
        "machine learning",
        "nlp",
        "intelligence artificielle",
        "data analyst",
        "analyste",
        "devops",
        "cloud",
        "ressources humaines",
        "rh",
        "administrateur",
        "commercial",
        "chauffeur",
    ]
    found: list[str] = []
    for keyword in ordered_keywords:
        if keyword in folded and keyword not in found:
            found.append(keyword)

    normalized_skills = {_fold_text(skill) for skill in (cv_analysis.skills or [])}
    skill_to_keywords = {
        "python": ["developpeur python", "python", "backend"],
        "fastapi": ["developpeur python", "api", "backend"],
        "django": ["developpeur python", "backend"],
        "flask": ["developpeur python", "api"],
        "java": ["developpeur java", "backend"],
        "spring": ["developpeur java", "backend"],
        "spring boot": ["developpeur java", "backend"],
        "react": ["frontend", "react", "javascript"],
        "typescript": ["frontend", "typescript", "full stack"],
        "javascript": ["frontend", "javascript", "full stack"],
        "node.js": ["backend", "node", "full stack"],
        "node": ["backend", "node", "full stack"],
        "nestjs": ["backend", "node", "full stack"],
        "machine learning": ["ingenieur ia", "machine learning", "data scientist"],
        "nlp": ["nlp", "ingenieur ia", "machine learning"],
        "llm": ["ingenieur ia", "nlp", "machine learning"],
        "spark": ["data engineer", "ingenieur data"],
        "kafka": ["data engineer", "ingenieur data"],
        "airflow": ["data engineer", "ingenieur data"],
        "docker": ["backend", "devops"],
        "kubernetes": ["devops", "cloud"],
        "terraform": ["devops", "cloud"],
        "sql": ["data analyst", "data engineer"],
        "power bi": ["data analyst", "analyste"],
        "tableau": ["data analyst", "analyste"],
        "php": ["developpeur", "full stack"],
        "laravel": ["developpeur", "full stack"],
    }
    for skill, keywords in skill_to_keywords.items():
        if skill in normalized_skills:
            for keyword in keywords:
                if keyword not in found:
                    found.append(keyword)
    return found


def _is_low_quality_job_title(title: str | None) -> bool:
    normalized = _fold_text(title)
    if normalized in LOW_QUALITY_JOB_TITLES:
        return True
    if len(re.sub(r"[^a-z0-9]+", "", normalized)) < 4:
        return True
    return bool(re.fullmatch(r"p\d+", normalized))
