"""Task processing helpers for CV text recommendation flows."""

from __future__ import annotations

from core.task_tracker import TaskStatus, get_task_tracker

from services.cv_analyzer import (
    extract_education_level,
    extract_experience_years,
    extract_skills_from_text,
)

from .models import CVAnalysisResult

__all__ = ["process_cv_text_analysis"]


async def process_cv_text_analysis(
    task_id: str,
    cv_text: str,
    file_name: str,
):
    """
    Analyse CV texte brut en arrière-plan.
    Met à jour progression dans Redis.

    Étapes:
    1. Validation texte (30%)
    2. Extraction compétences (60%)
    3. Extraction expérience (80%)
    4. Extraction éducation (100%)
    """
    tracker = get_task_tracker()

    try:
        tracker.update_progress(task_id, 10, "Validation du CV...", TaskStatus.PROCESSING)

        if len(cv_text.strip()) < 10:
            tracker.fail_task(task_id, "CV trop court (min 10 caractères)")
            return

        tracker.update_progress(
            task_id,
            35,
            "Extraction des compétences techniques...",
            TaskStatus.PROCESSING,
        )
        skills = extract_skills_from_text(cv_text)

        tracker.update_progress(
            task_id,
            65,
            "Extraction de l'expérience professionnelle...",
            TaskStatus.PROCESSING,
        )
        experience_years = extract_experience_years(cv_text)

        tracker.update_progress(
            task_id,
            85,
            "Analyse du niveau d'études...",
            TaskStatus.PROCESSING,
        )
        education_level = extract_education_level(cv_text)

        tracker.update_progress(task_id, 95, "Sauvegarde des résultats...", TaskStatus.PROCESSING)

        preview = cv_text[:200].replace("\n", " ")
        result = CVAnalysisResult(
            skills=skills,
            experience_years=experience_years,
            education_level=education_level,
            raw_text_preview=preview,
        )

        tracker.complete_task(task_id, result.dict())

    except Exception as e:
        tracker.fail_task(task_id, f"Erreur analyse: {str(e)}")
