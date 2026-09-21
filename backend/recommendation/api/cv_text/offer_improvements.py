"""Offer-specific CV improvement helpers."""

from __future__ import annotations

import re

from services.cv_analyzer import extract_skills_from_text

from .models import CVAnalysisResult
from .parsing_core import (
    _extract_required_experience_years,
    _job_mentions_education_requirement,
    _normalize_skill_name,
)

__all__ = [
    "_deterministic_offer_improvements",
    "_build_offer_improvement_prompt",
    "_parse_improvement_bullets",
    "_is_improvement_response_usable",
]


def _deterministic_offer_improvements(
    *,
    cv_analysis: CVAnalysisResult,
    job_title: str,
    job_summary: str,
    missing_skills: list[str],
) -> list[str]:
    improvements: list[str] = []
    title = (job_title or "").strip()
    job_text = f"{job_title} {job_summary}".strip()
    job_skills = extract_skills_from_text(job_text)
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    matching_skills = [s for s in job_skills if _normalize_skill_name(s) in cv_skill_set]

    improvements.append(f"Adapte l'en-tête du CV au poste ciblé : '{title}'.")
    if missing_skills:
        improvements.append(
            "Ajoute ces compétences manquantes (si réellement maîtrisées) : "
            + ", ".join(missing_skills[:5])
            + "."
        )
    if matching_skills:
        improvements.append(
            "Mets en avant ces compétences déjà alignées dès le résumé : "
            + ", ".join(matching_skills[:5])
            + "."
        )

    improvements.append("Réécris 2 expériences avec résultats chiffrés (KPI, délai, coût, qualité).")

    if cv_analysis.experience_years is None:
        improvements.append("Précise explicitement tes années d'expérience par techno/projet.")
    else:
        required_years = _extract_required_experience_years(job_text)
        if required_years is not None and cv_analysis.experience_years < required_years:
            improvements.append(
                f"Le poste semble demander ~{required_years}+ ans : détaille les missions les plus avancées que tu as déjà réalisées."
            )

    if not cv_analysis.education_level:
        if _job_mentions_education_requirement(job_text):
            improvements.append("Ajoute la section formation avec niveau, spécialité et année.")
        else:
            improvements.append("Ajoute la section formation/certifications avec niveau et année.")

    seen = set()
    out = []
    for item in improvements:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out[:8]


def _build_offer_improvement_prompt(
    *,
    cv_analysis: CVAnalysisResult,
    job_title: str,
    job_summary: str,
    job_url: str | None,
    missing_skills: list[str],
    deterministic_improvements: list[str],
    output_language: str = "fr",
) -> str:
    lang = (output_language or "fr").lower()
    if lang == "en":
        return (
            "You are a CV coach. Write in clear English and stay concrete.\n"
            "Return only a bullet list of 5 to 8 targeted CV improvements for this job.\n"
            "Each bullet must be actionable (verb + concrete detail), with no fluff.\n\n"
            f"Job:\n- title: {job_title}\n- url: {job_url or 'N/A'}\n- summary: {job_summary or 'N/A'}\n\n"
            f"CV:\n- skills: {', '.join(cv_analysis.skills) or 'N/A'}\n"
            f"- experience_years: {cv_analysis.experience_years}\n"
            f"- education_level: {cv_analysis.education_level}\n"
            f"- preview: {cv_analysis.raw_text_preview}\n\n"
            f"Detected missing skills: {', '.join(missing_skills) if missing_skills else 'None'}\n"
            "Current deterministic baseline:\n- " + "\n- ".join(deterministic_improvements) + "\n"
        )

    return (
        "Tu es un coach CV. Réponds en français, concret, sans blabla.\n"
        "Rends uniquement une liste de 5 à 8 puces d'amélioration CV ciblées pour l'offre.\n"
        "Chaque puce doit être actionnable (verbe d'action + détail concret).\n\n"
        f"Offre:\n- titre: {job_title}\n- url: {job_url or 'N/A'}\n- résumé: {job_summary or 'N/A'}\n\n"
        f"CV:\n- skills: {', '.join(cv_analysis.skills) or 'N/A'}\n"
        f"- experience_years: {cv_analysis.experience_years}\n"
        f"- education_level: {cv_analysis.education_level}\n"
        f"- preview: {cv_analysis.raw_text_preview}\n\n"
        f"Compétences manquantes détectées : {', '.join(missing_skills) if missing_skills else 'Aucune'}\n"
        "Base déterministe actuelle :\n- " + "\n- ".join(deterministic_improvements) + "\n"
    )


def _parse_improvement_bullets(text: str) -> list[str]:
    lines = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*•\d\)\.\s]+", "", line).strip()
        if line:
            lines.append(line)
    if len(lines) <= 1:
        candidates = [s.strip() for s in re.split(r"[.;]\s+", text or "") if s.strip()]
        lines = candidates

    seen = set()
    out = []
    for line in lines:
        if len(line) < 12:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out[:8]


def _is_improvement_response_usable(lines: list[str]) -> bool:
    if not lines or len(lines) < 3:
        return False

    text = " ".join(lines).lower()
    bad_tokens = (
        "tu es un coach cv",
        "réponds en français",
        "rends uniquement",
        "skills:",
        "experience_years",
        "education_level",
        "titre:",
        "url:",
        "résumé:",
    )
    if any(tok in text for tok in bad_tokens):
        return False
    return True
