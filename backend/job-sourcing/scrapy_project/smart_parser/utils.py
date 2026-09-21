# Utilitaires partages du moteur d'extraction
# Normalisation texte, extraction regex, detection pays, scoring

import re
import unicodedata
from typing import Optional

from scrapy.http import HtmlResponse

from .constants import COUNTRY_MAP, JOB_INDICATORS


def normalize_text(text: str) -> str:
    """Normalise un texte : NFC unicode, espaces multiples, strip."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_all_text(response: HtmlResponse, selector: str) -> str:
    """Extrait tout le texte d'un element, incluant les sous-elements."""
    elements = response.css(selector)
    if not elements:
        return ""
    texts = elements.css("*::text").getall()
    return normalize_text(" ".join(t.strip() for t in texts if t.strip()))


def extract_pattern(text: str, patterns: list) -> Optional[str]:
    """Recherche un champ dans le texte via des patterns regex."""
    if not text:
        return None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group(1).strip() if match.lastindex else match.group(0).strip()
            if result:
                return result
    return None


def looks_like_job_page(title: str, description: str, url: str) -> bool:
    """
    Heuristique pour determiner si une page est une offre d'emploi INDIVIDUELLE.
    Exclut les pages de listing/recherche/pagination.
    Score >= 2 indicateurs = page d'offre probable.
    """
    # Exclure les pages de listing/recherche par le titre
    listing_patterns = [
        r'offres?\s+d.emploi\s*:', r'annonces?\s+de\s+recrutement',
        r'recherche\s+(?:d.)?emploi', r'r[eé]sultats?\s+de\s+recherche',
        r'toutes?\s+les?\s+offres?', r'les\s+annonces',
        r'emploi\s+[-\u2013]\s+page', r'job\s+listings?',
        r'browse\s+jobs', r'search\s+results',
    ]
    title_lower = title.lower() if title else ""
    for pat in listing_patterns:
        if re.search(pat, title_lower):
            return False

    # Exclure les URLs de pagination explicites
    url_lower = url.lower()
    if re.search(r'[?&]page=\d+', url_lower) and not re.search(r'/job[-_]?\d+', url_lower):
        return False

    # Exclure les pages entreprise/profil (pas une offre)
    company_page_patterns = [
        r'agences?\s+de\s+recrutement$',
        r'cabinet\s+de\s+recrutement$',
        r'soci[eé]t[eé]\s+de\s+services?$',
        r'^\w+\s*[-\u2013]\s*(?:agences?|cabinet|soci)',
    ]
    for pat in company_page_patterns:
        if re.search(pat, title_lower):
            return False

    combined = f"{title} {description} {url}".lower()
    score = sum(1 for pat in JOB_INDICATORS if re.search(pat, combined))
    return score >= 2


def detect_country(response: HtmlResponse, full_text: str) -> str:
    """Detecte le pays depuis l'URL et le contenu textuel."""
    combined = f"{response.url} {full_text}".lower()
    for country, keywords in COUNTRY_MAP.items():
        for kw in keywords:
            if kw in combined:
                return country
    return "Afrique"


def get_body_text(response: HtmlResponse, max_elements: int = 300) -> str:
    """Extrait le texte brut du body pour analyse heuristique."""
    texts = response.css("body *::text").getall()[:max_elements]
    return " ".join(t.strip() for t in texts if t.strip())
