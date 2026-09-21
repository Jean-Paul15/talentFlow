"""
Extraction des features pour le ranking.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime


def calculate_history_score(
    user_history: Optional[List[Dict]],
    job: Dict[str, Any]
) -> float:
    """Score basé sur l'historique utilisateur (clics, candidatures)."""
    if not user_history:
        return 0.0
    score = 0.0
    job_company = job.get('company')
    job_title = job.get('title', '').lower()
    for interaction in user_history:
        if interaction.get('company') == job_company:
            score += 0.3
        if interaction.get('title', '').lower() in job_title:
            score += 0.4
        action = interaction.get('action')
        if action == 'applied':
            score += 0.8
        elif action == 'saved':
            score += 0.5
        elif action == 'clicked':
            score += 0.2
    return min(score, 1.0)


def extract_features(
    cv_profile: Dict[str, Any],
    job: Dict[str, Any],
    user_history: Optional[List[Dict]] = None
) -> Dict[str, float]:
    """Extrait les features pour le ranking ML (robuste aux manquants)."""
    features: Dict[str, float] = {}
    cv_skills = set(cv_profile.get('skills', []))
    job_skills = set(job.get('required_skills', []))
    features['skills_overlap_ratio'] = (
        len(cv_skills & job_skills) / len(job_skills)
        if job_skills else 0.5
    )
    cv_exp = cv_profile.get('years_experience', 0)
    job_exp = job.get('required_experience', 0)
    features['experience_match'] = min(cv_exp / max(job_exp, 1), 1.5)
    features['semantic_similarity'] = float(job.get('_score', 0.0))
    features['location_match'] = float(
        cv_profile.get('location') == job.get('location')
    )
    features['user_history_score'] = calculate_history_score(user_history, job)
    cv_salary = cv_profile.get('expected_salary', 0)
    job_salary = job.get('salary', 0)
    features['salary_ratio'] = job_salary / cv_salary if cv_salary > 0 else 0.5
    posted_date = job.get('posted_date')
    if isinstance(posted_date, str):
        posted_date = datetime.fromisoformat(posted_date)
    features['days_since_posted'] = (
        (datetime.now() - posted_date).days if posted_date else 30
    )
    features['company_rating'] = job.get('company_rating', 3.0)
    cv_edu = cv_profile.get('education_level', 0)
    job_edu = job.get('required_education', 0)
    features['education_match'] = float(cv_edu >= job_edu)
    features['contract_type_match'] = float(
        cv_profile.get('preferred_contract') == job.get('contract_type')
    )
    return features
