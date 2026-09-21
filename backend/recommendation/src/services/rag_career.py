"""
Génération de conseils carrière pour RAG.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def generate_career_advice(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]],
    llm_client: Optional[Any] = None
) -> str:
    """Génère des conseils carrière via LLM."""
    try:
        if not llm_client:
            return _generate_fallback_advice(cv_profile, matched_jobs)
        prompt = _build_career_advice_prompt(cv_profile, matched_jobs)
        advice = await llm_client.generate(
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        return advice
    except Exception as e:
        logger.error(f"Erreur génération conseils carrière: {e}")
        return _generate_fallback_advice(cv_profile, matched_jobs)


def _build_career_advice_prompt(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]]
) -> str:
    """Construit le prompt pour conseils carrière."""
    skills = cv_profile.get('skills', [])
    experience_years = cv_profile.get('experience_years', 0)
    job_titles = [job.get('title', '') for job in matched_jobs[:5]]
    prompt = f"""En tant que conseiller carrière, analysez ce profil:
- Compétences: {', '.join(skills)}
- Années d'expérience: {experience_years}
- Opportunités correspondantes: {', '.join(job_titles)}

Donnez 3 conseils concrets pour maximiser les chances de succès."""
    return prompt


def _generate_fallback_advice(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]]
) -> str:
    """Conseils génériques sans LLM."""
    experience_years = cv_profile.get('experience_years', 0)
    if experience_years < 2:
        return "Concentrez-vous sur des postes juniors. Valorisez vos projets académiques et stages."
    elif experience_years < 5:
        return "Ciblez des postes intermédiaires. Mettez en avant vos réalisations concrètes."
    else:
        return "Explorez des postes seniors ou lead. Soulignez votre leadership et impact métier."
