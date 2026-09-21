# Nettoyeur de texte avec Unstructured
# Extrait et normalise le contenu des descriptions

import re
from typing import Optional

from loguru import logger

from processors.normalizers import (
    normalize_contract_type,
    normalize_country,
    normalize_location,
)

try:
    from unstructured.cleaners.core import (
        clean,
        clean_extra_whitespace,
        replace_unicode_quotes,
    )
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logger.warning("Unstructured non disponible")


class TextCleaner:
    """
    Nettoie et normalise les textes des offres d'emploi.
    """
    
    def __init__(self):
        """
        Initialise le nettoyeur.
        """
        self.use_unstructured = UNSTRUCTURED_AVAILABLE
        logger.info(f"TextCleaner: unstructured={self.use_unstructured}")
    
    def clean_text(self, text: Optional[str]) -> str:
        """
        Nettoie un texte brut.
        """
        if not text:
            return ""
        
        if self.use_unstructured:
            return self._clean_unstructured(text)
        return self._clean_regex(text)
    
    def _clean_unstructured(self, text: str) -> str:
        """
        Nettoyage avec Unstructured.
        """
        text = replace_unicode_quotes(text)
        text = clean_extra_whitespace(text)
        text = clean(text, bullets=True, extra_whitespace=True)
        return text.strip()
    
    def _clean_regex(self, text: str) -> str:
        """
        Nettoyage fallback avec regex.
        """
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def normalize_location(self, location: Optional[str]) -> str:
        """
        Proxy vers le normaliseur de location.
        """
        cleaned = self.clean_text(location)
        return normalize_location(cleaned)
    
    def normalize_contract_type(self, contract: Optional[str]) -> Optional[str]:
        """
        Proxy vers le normaliseur de contrat.
        """
        return normalize_contract_type(contract)

    def normalize_country(
        self,
        country: Optional[str],
        *,
        location: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> str:
        """
        Proxy vers le normaliseur de pays.
        """
        return normalize_country(country, location=location, source_name=source_name)
