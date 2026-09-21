"""Lightweight ATS scoring helpers for CV recommendations."""

from __future__ import annotations

import re

from .models import CVAnalysisResult, RecommendedJobPreview
from services.cv_analyzer import extract_skills_from_text

from .parsing_core import _normalize_skill_name
from .parsing_geo import _recommendation_alignment_signals
from .text_utils import _fold_text

__all__ = [
    "_clamp_percent",
    "_score_cv_structure",
    "_score_cv_evidence",
    "_ats_readiness_label",
    "_build_ats_lite_payload",
]


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _score_cv_structure(cv_text: str, cv_analysis: CVAnalysisResult) -> int:
    text = cv_text or ""
    lowered = _fold_text(text)
    score = 28
    if len(text) >= 250:
        score += 8
    if len(text) >= 600:
        score += 6
    if "@" in text:
        score += 10
    if re.search(r"(\+?\d[\d\s().-]{7,}\d)", text):
        score += 8
    if any(token in lowered for token in ("experience", "expérien", "missions", "projects", "projets")):
        score += 14
    if any(token in lowered for token in ("formation", "education", "universit", "licence", "master", "bts", "dut")):
        score += 10
    if any(token in lowered for token in ("competences", "skills", "outils", "technologies")):
        score += 10
    if cv_analysis.skills or []:
        score += min(12, len(cv_analysis.skills) * 2)
    if cv_analysis.experience_years is not None:
        score += 10
    return _clamp_percent(score)


def _score_cv_evidence(cv_text: str, cv_analysis: CVAnalysisResult) -> int:
    text = cv_text or ""
    bullets = len(re.findall(r"(?m)^\s*[-*•]", text))
    digit_groups = len(re.findall(r"\b\d+(?:[.,]\d+)?\b", text))
    score = 24
    score += min(18, bullets * 4)
    score += min(22, digit_groups * 3)
    if cv_analysis.experience_years is not None:
        score += 10
    if any(token in _fold_text(text) for token in ("ameliore", "réduit", "increase", "optimis", "deploi", "dashboard", "reporting")):
        score += 14
    return _clamp_percent(score)


def _ats_readiness_label(score: int) -> str:
    if score >= 80:
        return "Solide pour candidater"
    if score >= 65:
        return "Bon potentiel, quelques retouches"
    if score >= 50:
        return "Candidature exploitable mais perfectible"
    return "CV à renforcer avant d'envoyer"


def _build_ats_lite_payload(
    *,
    cv_text: str,
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    assistant_structured: dict,
) -> dict:
    cv_skill_set = {_normalize_skill_name(skill) for skill in (cv_analysis.skills or [])}
    top_jobs = jobs[:3]
    extracted_job_skills = extract_skills_from_text(" ".join(f"{job.title} {job.summary}" for job in top_jobs))
    unique_job_skills: list[str] = []
    seen_job_skills: set[str] = set()
    for skill in extracted_job_skills:
        normalized = _normalize_skill_name(skill)
        if not normalized or normalized in seen_job_skills:
            continue
        seen_job_skills.add(normalized)
        unique_job_skills.append(skill)
    matched_keywords = [skill for skill in unique_job_skills if _normalize_skill_name(skill) in cv_skill_set][:6]
    missing_keywords = [skill for skill in unique_job_skills if _normalize_skill_name(skill) not in cv_skill_set][:6]
    top_score = float(top_jobs[0].score or 0.0) if top_jobs else 0.0
    overlap_jobs, role_match_jobs = _recommendation_alignment_signals(
        jobs=top_jobs,
        cv_analysis=cv_analysis,
        cv_text=cv_text,
    )
    alignment_base = min(1.0, max(0.0, top_score))
    alignment_score = _clamp_percent(
        25 + alignment_base * 45 + overlap_jobs * 10 + role_match_jobs * 8 - min(18, len(missing_keywords) * 2.5)
    )
    structure_score = _score_cv_structure(cv_text, cv_analysis)
    evidence_score = _score_cv_evidence(cv_text, cv_analysis)
    overall_score = _clamp_percent(structure_score * 0.35 + alignment_score * 0.45 + evidence_score * 0.20)
    readiness_label = _ats_readiness_label(overall_score)
    suggestions: list[str] = []
    if structure_score < 70:
        suggestions.append("Ajoute un en-tête clair avec titre visé, email et téléphone.")
    if evidence_score < 65:
        suggestions.append("Transforme 2 expériences en réalisations chiffrées, pas seulement en tâches.")
    if missing_keywords:
        suggestions.append(
            "Intègre dans le CV les mots-clés réellement maîtrisés suivants: " + ", ".join(missing_keywords[:4]) + "."
        )
    if not matched_keywords:
        suggestions.append("Clarifie le métier ciblé et les outils principaux dès les premières lignes.")
    for item in assistant_structured.get("actions") or []:
        text = str(item).strip()
        if text:
            suggestions.append(text)
    deduped_suggestions: list[str] = []
    seen_suggestions: set[str] = set()
    for item in suggestions:
        key = _fold_text(item)
        if not key or key in seen_suggestions:
            continue
        seen_suggestions.add(key)
        deduped_suggestions.append(item)
        if len(deduped_suggestions) >= 4:
            break
    action_plan = [
        "Jour 1: nettoie le titre du CV et adapte le résumé au métier visé.",
        "Jour 2: ajoute les outils et compétences réellement maîtrisés qui manquent dans les offres cibles.",
        "Jour 3: réécris 2 expériences avec résultats chiffrés et impact concret.",
        "Jour 4-7: candidate d'abord sur les offres les plus alignées et sauvegarde les autres en veille.",
    ]
    if assistant_structured.get("mode") == "no_match":
        action_plan[-1] = "Jour 4-7: recentre la cible (poste, localisation, niveau) puis relance une analyse."
    summary = (
        f"Score global {overall_score}/100. "
        f"Structure {structure_score}/100, alignement {alignment_score}/100, preuves {evidence_score}/100."
    )
    return {
        "overall_score": overall_score,
        "structure_score": structure_score,
        "alignment_score": alignment_score,
        "evidence_score": evidence_score,
        "readiness_label": readiness_label,
        "summary": summary,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "suggestions": deduped_suggestions,
        "action_plan": action_plan,
    }
