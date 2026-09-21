"""Default structured assistant content for CV recommendations."""

from __future__ import annotations

from services.cv_analyzer import extract_skills_from_text

from .models import CVAnalysisResult, RecommendedJobPreview
from .parsing_core import _normalize_skill_name

__all__ = [
    "_default_profile_summary",
    "_default_strengths",
    "_default_gaps",
    "_default_actions",
    "_recommendation_structured_schema",
]


def _default_profile_summary(cv_analysis: CVAnalysisResult) -> str:
    skills = ", ".join((cv_analysis.skills or [])[:5])
    parts = []
    if skills:
        parts.append(f"Profil aligné sur {skills}")
    if cv_analysis.experience_years is not None:
        parts.append(f"avec environ {cv_analysis.experience_years} ans d'expérience")
    if cv_analysis.education_level:
        parts.append(f"et un niveau d'études estimé à {cv_analysis.education_level}")
    summary = " ".join(parts).strip()
    return (
        summary
        or "Profil partiellement analysé: précise davantage tes compétences et tes expériences clés."
    )


def _default_strengths(cv_analysis: CVAnalysisResult) -> list[str]:
    strengths: list[str] = []
    for skill in (cv_analysis.skills or [])[:3]:
        strengths.append(f"Compétence détectée: {skill}")
    if cv_analysis.experience_years is not None:
        strengths.append(f"Expérience identifiée: {cv_analysis.experience_years} ans")
    if cv_analysis.education_level:
        strengths.append(f"Niveau d'études identifié: {cv_analysis.education_level}")
    return strengths[:3] or ["CV suffisamment exploitable pour un premier matching"]


def _default_gaps(cv_analysis: CVAnalysisResult, jobs: list[RecommendedJobPreview]) -> list[str]:
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    job_skills = extract_skills_from_text(" ".join([f"{job.title} {job.summary}" for job in jobs[:3]]))
    missing = [skill for skill in job_skills if _normalize_skill_name(skill) not in cv_skill_set]
    gaps: list[str] = []
    if missing:
        gaps.append("Compétences à renforcer: " + ", ".join(missing[:3]))
    if cv_analysis.experience_years is None:
        gaps.append("Années d'expérience non explicites dans le CV")
    if not cv_analysis.education_level:
        gaps.append("Niveau d'études non explicite")
    gaps.append("Titre du CV et expériences à aligner plus clairement avec le poste visé")
    return gaps[:4]


def _default_actions(
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
) -> list[str]:
    top_job = jobs[0] if jobs else None
    target_title = (top_job.title if top_job else "").strip()
    job_skills = extract_skills_from_text(
        " ".join([f"{job.title} {job.summary}" for job in jobs[:3]])
    )
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    missing_skills = [
        skill for skill in job_skills if _normalize_skill_name(skill) not in cv_skill_set
    ][:3]
    aligned_skills = [
        skill for skill in job_skills if _normalize_skill_name(skill) in cv_skill_set
    ][:3]

    title_hint = target_title or "poste vise"
    skills_hint = ", ".join(missing_skills) if missing_skills else "competences cles du poste"
    aligned_hint = ", ".join(aligned_skills) if aligned_skills else "tes missions les plus proches"
    years_hint = (
        f"{cv_analysis.experience_years} ans"
        if cv_analysis.experience_years is not None
        else "ton nombre d'années"
    )

    actions = [
        (
            "Section Titre (en-tête): remplace le titre actuel par "
            f"\"{title_hint}\" et garde la meme formulation sur CV + LinkedIn."
        ),
        (
            "Section Résumé (3 lignes max): ajoute ton niveau, "
            f"tes forces ({aligned_hint}) et ton expérience ({years_hint})."
        ),
        (
            "Section Expériences: réécris 2 missions avec le format "
            "\"contexte -> action -> résultat chiffré\" (%, délai, volume, coût)."
        ),
        (
            "Section Compétences: ajoute uniquement les outils réellement maîtrisés attendus "
            f"({skills_hint}) et retire les technologies non utilisées récemment."
        ),
        (
            "Sections Projets/Certifications/Centres d'intérêt: ajoute un projet ou une certification récent(e), "
            "puis 1 centre d'intérêt pertinent pour le poste visé, avec une preuve de résultat concret."
        ),
    ]
    return actions[:5]


def _recommendation_structured_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["match", "no_match"]},
            "profile_summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "gaps": {"type": "array", "items": {"type": "string"}},
            "recommended_jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string"},
                        "title": {"type": "string"},
                        "why": {"type": "string"},
                        "url": {"type": "string"},
                        "cv_improvement": {"type": "string"},
                    },
                    "required": ["job_id", "title", "why", "url", "cv_improvement"],
                },
            },
            "score_explanation": {"type": "string"},
            "offer_playbooks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string"},
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "why_fit": {"type": "string"},
                        "cv_delta": {"type": "string"},
                        "rewrite": {
                            "type": "object",
                            "properties": {
                                "target_title": {"type": "string"},
                                "target_summary": {"type": "string"},
                                "experience_bullets": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["target_title", "target_summary", "experience_bullets"],
                        },
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["job_id", "title", "url", "why_fit", "cv_delta", "rewrite", "evidence"],
                },
            },
            "actions": {"type": "array", "items": {"type": "string"}},
            "reason_if_no_match": {"type": "string"},
        },
        "required": [
            "mode",
            "profile_summary",
            "strengths",
            "gaps",
            "recommended_jobs",
            "score_explanation",
            "offer_playbooks",
            "actions",
            "reason_if_no_match",
        ],
    }
