"""Core CV parsing helpers used by recommendation flows."""

from __future__ import annotations

import re

from .budget import _env_int
from .models import CVAnalysisResult, RecommendedJobPreview
from services.cv_analyzer import extract_skills_from_text

from .text_utils import _canonicalize_url, _fold_text

__all__ = [
    "_no_match_reason",
    "_fallback_job_why",
    "_llm_decision_for_offer_improvement",
    "_detect_cv_language",
    "_normalize_skill_name",
    "_extract_required_experience_years",
    "_job_mentions_education_requirement",
    "_build_default_offer_playbook",
    "_build_default_score_explanation",
    "_suggest_cv_improvement_for_job",
    "_is_llm_response_usable",
]


def _no_match_reason(decision_reason: str) -> str:
    mapping = {
        "no_meaningful_jobs": "Aucune offre suffisamment pertinente n'a été retenue pour ce profil.",
        "missing_scores": "Le moteur n'a pas obtenu assez de signaux de pertinence fiables.",
        "low_confidence_top_score": "Les offres trouvées sont trop éloignées du profil pour recommander une candidature immédiate.",
        "tight_score_gap": "Les meilleures offres sont trop proches entre elles sans signal d'alignement suffisamment net.",
        "too_few_meaningful_jobs": "Trop peu d'offres dépassent le seuil de confiance requis.",
        "low_skill_role_alignment": "Les offres trouvées restent trop peu alignées avec les compétences et le rôle visés.",
    }
    return mapping.get(
        decision_reason,
        "Aucune offre réellement pertinente n'a été retenue pour ce profil pour le moment.",
    )


def _fallback_job_why(cv_analysis: CVAnalysisResult, job: RecommendedJobPreview) -> str:
    why = []
    if cv_analysis.skills:
        why.append("les compétences détectées recoupent le poste")
    if job.location:
        why.append(f"la localisation cible est {job.location}")
    elif job.country:
        why.append(f"le poste se situe en {job.country}")
    if job.contract_type:
        why.append(f"type de contrat: {job.contract_type}")
    return ", ".join(why[:3]) or "le moteur de recherche a retenu ce poste comme le plus proche du profil"


def _llm_decision_for_offer_improvement(
    *,
    cv_analysis: CVAnalysisResult,
    job_title: str,
    job_summary: str,
    missing_skills: list[str],
) -> tuple[bool, str]:
    min_missing = _env_int("LLM_DECISION_OFFER_MIN_MISSING_SKILLS", 2)
    if len(missing_skills) >= max(1, min_missing):
        return True, "multiple_missing_skills"

    job_text = f"{job_title} {job_summary}".strip()
    required_years = _extract_required_experience_years(job_text)
    if (
        required_years is not None
        and cv_analysis.experience_years is not None
        and cv_analysis.experience_years < required_years
    ):
        return True, "experience_gap"

    if len(job_summary or "") >= _env_int("LLM_DECISION_OFFER_SUMMARY_MIN_CHARS", 500):
        return True, "long_offer_context"

    return False, "deterministic_sufficient"


def _detect_cv_language(cv_text: str) -> str:
    text = _fold_text(cv_text)
    if not text:
        return "fr"
    fr_hits = sum(
        1
        for token in (
            "experience",
            "competences",
            "formation",
            "profil",
            "entreprise",
            "mission",
            "stage",
            "candidature",
        )
        if token in text
    )
    en_hits = sum(
        1
        for token in (
            "experience",
            "skills",
            "education",
            "profile",
            "company",
            "internship",
            "resume",
            "application",
        )
        if token in text
    )
    es_hits = sum(
        1
        for token in (
            "experiencia",
            "habilidades",
            "educacion",
            "perfil",
            "empresa",
            "candidatura",
            "curriculum",
        )
        if token in text
    )
    if en_hits >= fr_hits + 2 and en_hits >= es_hits:
        return "en"
    if es_hits >= fr_hits + 2 and es_hits >= en_hits:
        return "es"
    return "fr"


def _normalize_skill_name(skill: str) -> str:
    return re.sub(r"\s+", " ", (skill or "").strip().lower())


def _build_default_score_explanation(
    *,
    overall_score: int,
    structure_score: int,
    alignment_score: int,
    evidence_score: int,
    language: str = "fr",
) -> str:
    target = min(95, max(overall_score + 12, 72))
    if language == "en":
        return (
            f"Current score: {overall_score}/100. Target: {target}/100. "
            f"Focus first on structure ({structure_score}/100), role alignment ({alignment_score}/100), "
            f"and proof quality ({evidence_score}/100). "
            "Improve your title/summary for the target role and add 2 measurable achievements."
        )
    if language == "es":
        return (
            f"Puntuacion actual: {overall_score}/100. Objetivo: {target}/100. "
            f"Prioriza estructura ({structure_score}/100), alineacion con el puesto ({alignment_score}/100) "
            f"y evidencias ({evidence_score}/100). "
            "Reformula titulo/resumen y anade 2 logros medibles."
        )
    return (
        f"Score actuel: {overall_score}/100. Cible: {target}/100. "
        f"Priorite sur la structure ({structure_score}/100), l'alignement ({alignment_score}/100) "
        f"et les preuves ({evidence_score}/100). "
        "Actions concrètes: titre aligné au poste, résumé ciblé en 3 lignes, puis 2 réalisations chiffrées liées au rôle."
    )


def _build_default_offer_playbook(
    *,
    cv_analysis: CVAnalysisResult,
    job: RecommendedJobPreview,
    language: str = "fr",
) -> dict[str, object]:
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    job_text = " ".join(
        [str(job.title or ""), str(job.summary or ""), str(job.contract_type or ""), str(job.location or "")]
    ).strip()
    job_skills = extract_skills_from_text(job_text)
    missing_skills = [s for s in job_skills if _normalize_skill_name(s) not in cv_skill_set][:4]
    aligned_skills = [s for s in job_skills if _normalize_skill_name(s) in cv_skill_set][:4]

    if language == "en":
        why_fit = _fallback_job_why(cv_analysis, job)
        cv_delta = (
            "Section Skills: add evidence for missing skills: " + ", ".join(missing_skills)
            if missing_skills
            else "Section Experience: strengthen measurable impact for similar missions."
        )
        target_summary = (
            f"Candidate profile aligned with {', '.join(aligned_skills) or 'the target role'}, "
            "with operational delivery and measurable outcomes."
        )
        experience_bullets = [
            "Section Experience: rewrite one mission using context -> action -> quantified impact.",
            "Section Experience: add one measurable result directly linked to this role.",
            "Section Skills: mention tools actually used in that mission and the business gain.",
        ]
        evidence = [
            f"Detected skills in CV: {', '.join((cv_analysis.skills or [])[:4]) or 'n/a'}",
            f"Detected experience: {cv_analysis.experience_years if cv_analysis.experience_years is not None else 'n/a'} years",
        ]
    elif language == "es":
        why_fit = _fallback_job_why(cv_analysis, job)
        cv_delta = (
            "Seccion Habilidades: reforzar " + ", ".join(missing_skills)
            if missing_skills
            else "Seccion Experiencia: reforzar evidencias e impacto medible."
        )
        target_summary = (
            f"Perfil orientado a {', '.join(aligned_skills) or 'el puesto objetivo'}, "
            "con ejecucion operativa y resultados medibles."
        )
        experience_bullets = [
            "Seccion Experiencia: reescribe una mision en formato contexto -> accion -> impacto cuantificado.",
            "Seccion Experiencia: anade un resultado medible ligado al puesto objetivo.",
            "Seccion Habilidades: cita herramientas reales usadas en la mision y su impacto.",
        ]
        evidence = [
            f"Competencias detectadas en el CV: {', '.join((cv_analysis.skills or [])[:4]) or 'n/a'}",
            f"Experiencia detectada: {cv_analysis.experience_years if cv_analysis.experience_years is not None else 'n/a'} anos",
        ]
    else:
        why_fit = _fallback_job_why(cv_analysis, job)
        cv_delta = (
            "Section Compétences: renforcer " + ", ".join(missing_skills)
            if missing_skills
            else "Section Expériences: renforcer les preuves concrètes et l'impact mesurable."
        )
        target_summary = (
            f"Profil orienté {', '.join(aligned_skills) or 'poste cible'}, "
            "avec exécution opérationnelle et résultats mesurables sur des missions proches."
        )
        experience_bullets = [
            "Section Expériences: réécrire une mission en 3 lignes (contexte -> action -> résultat chiffré).",
            "Section Expériences: ajouter un résultat mesurable directement lié au poste (%, délai, volume).",
            "Section Compétences: citer les outils utilisés dans cette mission et le gain obtenu.",
        ]
        evidence = [
            f"Compétences détectées dans le CV: {', '.join((cv_analysis.skills or [])[:4]) or 'n/a'}",
            f"Expérience détectée: {cv_analysis.experience_years if cv_analysis.experience_years is not None else 'n/a'} an(s)",
        ]

    return {
        "job_id": job.id,
        "title": job.title,
        "url": _canonicalize_url(job.source_url),
        "why_fit": why_fit,
        "cv_delta": cv_delta,
        "rewrite": {
            "target_title": job.title,
            "target_summary": target_summary,
            "experience_bullets": experience_bullets[:3],
        },
        "evidence": [item for item in evidence if item][:3],
    }


def _extract_required_experience_years(text: str) -> int | None:
    txt = re.sub(r"\s+", " ", (text or "").lower())
    if not txt:
        return None
    range_match = re.search(
        r"(\d{1,2})\s*(?:-|a|à|to)\s*(\d{1,2})\s*(?:\+?\s*)?(?:ans?|annees?|années?|years?|yrs?)",
        txt,
    )
    if range_match:
        return max(int(range_match.group(1)), int(range_match.group(2)))
    years = [
        int(x)
        for x in re.findall(
            r"(\d{1,2})\s*\+?\s*(?:ans?|annees?|années?|years?|yrs?)",
            txt,
        )
    ]
    return max(years) if years else None


def _job_mentions_education_requirement(text: str) -> bool:
    txt = (text or "").lower()
    return bool(
        re.search(r"\b(bac\+\d|master|licence|bachelor|ingenieur|ingénieur|doctorat|phd|msc)\b", txt)
    )


def _suggest_cv_improvement_for_job(
    cv_analysis: CVAnalysisResult,
    job: RecommendedJobPreview,
) -> str:
    cv_skill_set = {_normalize_skill_name(s) for s in (cv_analysis.skills or [])}
    job_text = " ".join(
        [str(job.title or ""), str(job.summary or ""), str(job.contract_type or ""), str(job.location or "")]
    ).strip()
    job_skills = extract_skills_from_text(job_text)
    missing_skills = [s for s in job_skills if _normalize_skill_name(s) not in cv_skill_set]
    matching_skills = [s for s in job_skills if _normalize_skill_name(s) in cv_skill_set]
    if missing_skills:
        return (
            "Section Compétences: ajoute uniquement les compétences attendues "
            f"({', '.join(missing_skills[:3])}) si tu les maîtrises, puis ajoute 1 preuve chiffrée par compétence en section Expériences."
        )
    required_years = _extract_required_experience_years(job_text)
    if (
        required_years is not None
        and cv_analysis.experience_years is not None
        and cv_analysis.experience_years < required_years
    ):
        return (
            f"Section Expériences: le poste vise ~{required_years}+ ans; priorise tes missions les plus proches et ajoute un impact mesuré (délai, coût, qualité)."
        )
    if cv_analysis.experience_years is None:
        return "Section Résumé: précise explicitement tes années d'expérience par techno/projet pour améliorer le matching."
    if _job_mentions_education_requirement(job_text) and not cv_analysis.education_level:
        return "Section Formation: ajoute clairement diplôme, spécialité et année d'obtention."
    if matching_skills:
        return (
            f"Section Résumé/Titre: mets en avant les compétences déjà alignées ({', '.join(matching_skills[:3])}) "
            "et relie-les à 2 résultats chiffrés dans la section Expériences."
        )
    return "Section Titre + Expériences: aligne le titre sur l'offre et ajoute 2 réalisations chiffrées directement liées au poste."


def _is_llm_response_usable(text: str, jobs: list[RecommendedJobPreview]) -> bool:
    txt = (text or "").strip()
    if len(txt) < 180:
        return False
    lowered = txt.lower()
    prompt_leak_tokens = (
        "structure attendue",
        "objectif:",
        "contraintes:",
        "1) résumé du profil",
        "2) 3 forces",
    )
    if any(tok in lowered for tok in prompt_leak_tokens):
        return False
    for job in jobs[:5]:
        title = (job.title or "").strip()
        source_url = _canonicalize_url(job.source_url)
        if source_url and source_url in txt:
            return True
        if title:
            short = " ".join(title.split()[:3]).lower()
            if short and len(short) >= 10 and short in lowered:
                return True
    return False
