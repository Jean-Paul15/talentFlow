# Utilitaires pour normalisation et extraction de skills
# Fonctions partagees entre NER et patterns

import re
from typing import Set

from processors.skill_constants import TECH_PATTERNS


def extract_by_patterns(text: str) -> Set[str]:
    """
    Extraction par patterns regex de technologies.
    """
    skills = set()
    for pattern in TECH_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                skills.update([m.strip() for m in match if m])
            else:
                skills.add(match.strip())
    return skills


def normalize_skills(skills: Set[str]) -> Set[str]:
    """
    Normalise les skills (casse, doublons).
    """
    normalized = set()
    seen_lower = set()
    
    for skill in skills:
        skill_clean = skill.strip()
        if len(skill_clean) < 2:
            continue
        
        lower = skill_clean.lower()
        if lower not in seen_lower:
            seen_lower.add(lower)
            # Garder la casse pour acronymes
            if skill_clean.isupper() or any(c.isupper() for c in skill_clean[1:]):
                normalized.add(skill_clean)
            else:
                normalized.add(skill_clean.title())
    
    return normalized
