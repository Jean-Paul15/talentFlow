# Module d'extraction LLM pour enrichissement des offres
# Mode officiel: Gemini uniquement avec fallback par seconde cle.
# Si Gemini est indisponible, le pipeline reste en mode deterministe
# sans fallback local.

from .extractor import LLMExtractor
from .config import LLMConfig

__all__ = ["LLMExtractor", "LLMConfig"]
