"""
Formatage des résultats de matching.
"""
from typing import List, Dict, Any


def format_final_results(
    recommendations: List[Dict[str, Any]],
    method: str
) -> List[Dict[str, Any]]:
    """Formate les résultats finaux pour la réponse API."""
    formatted = []
    for i, job in enumerate(recommendations):
        formatted.append({
            "job_id": job.get('id'),
            "title": job.get('title'),
            "company": job.get('company'),
            "location": job.get('location'),
            "salary": {
                "min": job.get('salary_min'),
                "max": job.get('salary_max')
            },
            "required_skills": job.get('required_skills', []),
            "semantic_score": float(job.get('semantic_score', job.get('_score', 0))),
            "ml_score": float(job.get('ml_score', 0)),
            "final_rank": i + 1,
            "ranking_method": job.get('ranking_method', method),
            "contract_type": job.get('contract_type'),
            "remote_work": job.get('remote_work'),
            "experience_required": job.get('required_experience_years'),
            "seniority_level": job.get('seniority_level')
        })
    return formatted
