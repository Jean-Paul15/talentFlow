"""
Extraction de features pour le ranking ML.
Module séparé pour respecter la limite de 100 lignes.
"""
from typing import Dict, Any
from datetime import datetime
def extract_skills_overlap(job: Dict[str, Any], cv: Dict[str, Any]) -> float:
    """Calcule le ratio de chevauchement des compétences."""
    job_skills = set(job.get('skills_required', []))
    cv_skills = set(cv.get('skills', []))
    
    if not job_skills:
        return 0.5
    
    overlap = job_skills.intersection(cv_skills)
    return len(overlap) / len(job_skills)
def extract_experience_match(job: Dict[str, Any], cv: Dict[str, Any]) -> float:
    """Évalue l'adéquation de l'expérience."""
    required_years = job.get('experience_required', 0)
    cv_years = cv.get('years_experience', 0)
    
    if required_years == 0:
        return 1.0
    
    if cv_years < required_years * 0.8:
        return cv_years / (required_years * 0.8)
    elif cv_years > required_years * 2:
        return max(0.5, 1.0 - (cv_years - required_years * 2) / 10)
    else:
        return 1.0
def extract_location_match(job: Dict[str, Any], cv: Dict[str, Any]) -> float:
    """Évalue la correspondance géographique."""
    job_location = job.get('location', {})
    cv_location = cv.get('preferred_location', {})
    
    job_city = job_location.get('city', '').lower()
    cv_city = cv_location.get('city', '').lower()
    
    if job_city and cv_city and job_city == cv_city:
        return 1.0
    
    job_country = job_location.get('country', '').lower()
    cv_country = cv_location.get('country', '').lower()
    
    if job_country and cv_country and job_country == cv_country:
        return 0.6
    
    return 0.3
def extract_salary_ratio(job: Dict[str, Any], cv: Dict[str, Any]) -> float:
    """Calcule le ratio salarial (fallback 0.5 si données absentes)."""
    try:
        job_salary = job.get('salary_min', 0) or job.get('salary_max', 0)
        expected_salary = cv.get('expected_salary', 0)
        
        if not job_salary or not expected_salary:
            return 0.5
        
        ratio = job_salary / expected_salary
        
        if 0.8 <= ratio <= 1.2:
            return 1.0
        elif ratio < 0.8:
            return max(0.3, ratio / 0.8)
        else:
            return max(0.5, 1.0 - (ratio - 1.2) / 2)
    except (ZeroDivisionError, TypeError):
        return 0.5
def extract_days_since_posted(job: Dict[str, Any]) -> float:
    """Calcule le score de fraîcheur de l'offre."""
    try:
        posted_date = job.get('posted_date')
        if not posted_date:
            return 0.5
        
        if isinstance(posted_date, str):
            posted_date = datetime.fromisoformat(
                posted_date.replace('Z', '+00:00')
            )
        
        days = (datetime.now() - posted_date).days
        
        if days <= 7:
            return 1.0
        elif days <= 30:
            return 0.8
        elif days <= 60:
            return 0.5
        else:
            return max(0.2, 0.5 - days / 200)
    except (ValueError, TypeError):
        return 0.5
