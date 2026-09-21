# Extracteurs de metadonnees pour offres d'emploi
# Experience et niveau d'education

import re
from typing import List

from processors.skill_constants import (
    SOFT_SKILLS_FR,
    SOFT_SKILLS_EN,
    EXPERIENCE_PATTERNS,
    EDUCATION_MAPPING,
)


def extract_soft_skills(text: str) -> List[str]:
    """
    Extrait les soft skills par detection de mots-cles FR/EN.
    
    Args:
        text: Texte de l'offre d'emploi
    
    Returns:
        Liste des soft skills detectees (max 15)
    """
    text_lower = text.lower()
    found = set()
    
    for skill in SOFT_SKILLS_FR:
        if skill in text_lower:
            found.add(skill.title())
    
    for skill in SOFT_SKILLS_EN:
        if skill in text_lower:
            found.add(skill.title())
    
    return list(found)[:15]


def extract_experience(text: str) -> int:
    """
    Extrait le nombre d'annees d'experience requises.
    
    Args:
        text: Texte de l'offre d'emploi
    
    Returns:
        Nombre d'annees (0 si non trouve)
    """
    for pattern in EXPERIENCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                years = int(match.group(1))
                if 0 < years <= 30:
                    return years
            except (ValueError, IndexError):
                continue
    return 0


def extract_education(text: str) -> str:
    """
    Extrait le niveau d'education requis.
    
    Args:
        text: Texte de l'offre d'emploi
    
    Returns:
        Niveau d'education (ex: "Bac+5", "Non precise")
    """
    text_lower = text.lower()
    
    for pattern, level in EDUCATION_MAPPING.items():
        if re.search(pattern, text_lower):
            return level
    
    return "Non precise"
