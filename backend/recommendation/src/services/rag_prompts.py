"""
Prompts LLM pour Enhanced RAG.
"""


def build_profile_analysis_prompt(
    cv_text: str,
    cv_profile: dict
) -> str:
    """Construit prompt pour analyse profil."""
    return f"""Analyse ce profil professionnel et fournis une évaluation détaillée.

CV: {cv_text[:2000]}
Compétences: {cv_profile.get('skills', [])}
Expérience: {cv_profile.get('years_experience', 0)} ans

Format JSON:
{{
    "strengths": ["point fort 1", "point fort 2", "point fort 3"],
    "weaknesses": ["point faible 1", "point faible 2"],
    "experience_level": "Junior|Mid|Senior",
    "technical_depth": "Beginner|Intermediate|Expert",
    "soft_skills_assessment": "description brève"
}}"""


def build_market_insights_prompt(
    job_title: str,
    skills: list,
    stats: dict = None
) -> str:
    """Construit prompt pour insights marché."""
    stats_context = f"Statistiques réelles: {stats}" if stats else ""
    return f"""Analyse le marché de l'emploi pour "{job_title}" avec compétences {skills}.

{stats_context}

Format JSON:
{{
    "demand_trend": "Forte|Moyenne|Faible",
    "growth_rate": "pourcentage ou description",
    "hot_skills": ["compétence 1", "compétence 2", "compétence 3"],
    "emerging_technologies": ["tech 1", "tech 2"],
    "market_saturation": "Faible|Moyenne|Élevée"
}}"""


def build_salary_estimate_prompt(
    job_title: str,
    location: str,
    years_experience: int
) -> str:
    """Construit prompt pour estimation salaire."""
    return f"""Estime les salaires pour "{job_title}" à {location} avec {years_experience} ans d'expérience.

Format JSON:
{{
    "min_salary": nombre,
    "median_salary": nombre,
    "max_salary": nombre,
    "percentile_position": 50
}}"""
