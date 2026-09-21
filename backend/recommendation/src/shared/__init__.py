"""
Utilitaires partagés pour le service de recommendation.
"""
from .currency_utils import (
    detect_currency_from_location,
    detect_currency_from_profile,
    get_currency_from_request,
    get_default_currency,
    is_supported_currency,
)
from .gpu_utils import (
    get_device,
    get_embedding_model,
    check_gpu_availability,
)
from .cache_manager import CacheManager
from .cache_keys import generate_cache_key

__all__ = [
    "detect_currency_from_location",
    "detect_currency_from_profile",
    "get_currency_from_request",
    "get_default_currency",
    "is_supported_currency",
    "get_device",
    "get_embedding_model",
    "check_gpu_availability",
    "CacheManager",
    "generate_cache_key",
]
