"""
Formatage des recommandations pour RAG.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def format_job_recommendations(
    matched_jobs: List[Dict[str, Any]],
    max_recommendations: int = 5
) -> List[Dict[str, Any]]:
    """Formate les recommandations pour affichage."""
    try:
        formatted_jobs = []
        for job in matched_jobs[:max_recommendations]:
            formatted_job = {
                "id": job.get('id', ''),
                "title": job.get('title', 'Non spécifié'),
                "company": job.get('company_name', 'Non spécifié'),
                "location": job.get('location', 'Non spécifié'),
                "contract_type": job.get('contract_type', 'Non spécifié'),
                "salary": _format_salary(job),
                "match_score": round(job.get('score', 0.5), 2),
                "posted_date": job.get('posted_date', 'Non spécifié'),
                "skills_required": job.get('skills_required', [])[:5]
            }
            formatted_jobs.append(formatted_job)
        return formatted_jobs
    except Exception as e:
        logger.error(f"Erreur formatage recommandations: {e}")
        return []


def _format_salary(job: Dict[str, Any]) -> str:
    """Formate le salaire pour affichage."""
    salary_min = job.get('salary_min')
    salary_max = job.get('salary_max')
    currency = job.get('currency', 'EUR')
    if salary_min and salary_max:
        return f"{int(salary_min/1000)}K-{int(salary_max/1000)}K {currency}"
    elif salary_min:
        return f"À partir de {int(salary_min/1000)}K {currency}"
    else:
        return "Non communiqué"
