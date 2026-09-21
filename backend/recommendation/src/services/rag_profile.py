"""
Analyse du profil candidat pour RAG.
"""
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def analyze_candidate_profile(
    cv_profile: Dict[str, Any],
    matched_jobs: List[Dict[str, Any]],
    llm
) -> Dict[str, str]:
    """Analyse les forces et faiblesses du profil candidat."""
    try:
        skills = cv_profile.get('skills', [])
        experience_years = cv_profile.get('total_experience_years', 0)
        seniority = cv_profile.get('seniority_level', 'mid')
        job_skills = set()
        for job in matched_jobs[:10]:
            job_skills.update(s.lower() for s in job.get('required_skills', []))
        candidate_skills = set(s.lower() for s in skills)
        matching_skills = candidate_skills & job_skills
        missing_skills = job_skills - candidate_skills
        prompt = f"""Analyse ce profil de candidat et génère une évaluation concise:

PROFIL CANDIDAT:
- Compétences: {', '.join(skills[:10])}
- Expérience: {experience_years} ans
- Niveau: {seniority}

COMPÉTENCES DEMANDÉES PAR LE MARCHÉ (top offres):
- Matching: {', '.join(list(matching_skills)[:8])}
- Manquantes: {', '.join(list(missing_skills)[:8])}

Génère (format court, 2-3 lignes max):
1. FORCES: Compétences clés et atouts du profil
2. GAPS: Compétences à développer pour mieux matcher

Format de réponse (JSON):
{{
  "strengths": "...",
  "gaps": "..."
}}
"""
        response = llm.invoke(prompt)
        try:
            return json.loads(response)
        except Exception:
            lines = response.split('\n')
            return {
                "strengths": lines[0] if lines else "Profil solide",
                "gaps": lines[1] if len(lines) > 1 else "Continuer à se développer"
            }
    except Exception as e:
        logger.error(f"Erreur analyse profil: {e}")
        return {"strengths": "Analyse non disponible", "gaps": "Analyse non disponible"}
