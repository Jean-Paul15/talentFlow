# Package smart_parser - Moteur d'extraction intelligent multi-niveaux
# Re-exporte l'API publique pour compatibilite avec les imports existants

from .engine import smart_parse
from .detectors import (
    detect_job_links,
    detect_pagination_links,
    detect_external_apply_links,
    detect_apply_url,
    detect_recruiter_name,
)
from .utils import normalize_text
from .fingerprint import get_cache_stats

__all__ = [
    "smart_parse",
    "detect_job_links",
    "detect_pagination_links",
    "detect_external_apply_links",
    "detect_apply_url",
    "detect_recruiter_name",
    "normalize_text",
    "get_cache_stats",
]
