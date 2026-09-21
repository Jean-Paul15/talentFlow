"""
Extraction de features pour le training ML.
"""
from datetime import datetime
from typing import List
import pandas as pd

FEATURE_NAMES = [
    'skills_overlap_ratio',
    'experience_match',
    'semantic_similarity',
    'location_match',
    'user_history_score',
    'salary_ratio',
    'days_since_posted',
    'company_rating',
    'education_match',
    'contract_type_match'
]


def extract_features_from_row(row: pd.Series) -> List[float]:
    """Extrait les features depuis une ligne du DataFrame."""
    cv_skills = set(row.get('cv_skills', []))
    job_skills = set(row.get('job_skills', []))
    skills_overlap = (
        len(cv_skills & job_skills) / len(job_skills)
        if job_skills else 0.0
    )
    cv_exp = row.get('cv_experience', 0)
    job_exp = row.get('job_experience', 0)
    exp_match = min(cv_exp / max(job_exp, 1), 1.5)
    semantic_sim = 0.5
    location_match = float(row.get('cv_location') == row.get('job_location'))
    user_history_score = 0.0
    cv_salary = row.get('cv_salary', 0)
    job_salary = row.get('job_salary', 0)
    salary_ratio = job_salary / cv_salary if cv_salary > 0 else 1.0
    posted_date = row.get('posted_date')
    if isinstance(posted_date, str):
        posted_date = datetime.fromisoformat(posted_date)
    days_posted = (
        (datetime.now() - posted_date).days
        if posted_date else 30
    )
    company_rating = row.get('company_rating', 3.0)
    cv_edu = row.get('cv_education', 0)
    job_edu = row.get('job_education', 0)
    edu_match = float(cv_edu >= job_edu)
    contract_match = 0.5
    return [
        skills_overlap,
        exp_match,
        semantic_sim,
        location_match,
        user_history_score,
        salary_ratio,
        days_posted,
        company_rating,
        edu_match,
        contract_match
    ]
