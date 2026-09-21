# Utilitaires de normalisation de texte
# Suppression accents et ponctuation

import re
from typing import Optional


# Remplacement des accents francais
ACCENT_MAP = {
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "à": "a", "â": "a", "ä": "a",
    "ô": "o", "ö": "o",
    "ù": "u", "û": "u", "ü": "u",
    "î": "i", "ï": "i",
    "ç": "c",
}


def normalize_text(text: Optional[str]) -> str:
    """
    Normalise un texte pour comparaison.
    Supprime accents, ponctuation, espaces multiples.
    """
    if not text:
        return ""
    
    text = text.lower()
    
    for old, new in ACCENT_MAP.items():
        text = text.replace(old, new)
    
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()
