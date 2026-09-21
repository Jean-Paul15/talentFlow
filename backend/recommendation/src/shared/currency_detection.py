"""
Détection et gestion des devises.
"""
import logging
import os
from typing import Optional

from .currency_mapping import COUNTRY_CURRENCY_MAP, SUPPORTED_CURRENCIES

logger = logging.getLogger(__name__)


def detect_currency_from_location(location: Optional[str]) -> str:
    """Détecte la devise à partir de la localisation."""
    if not location:
        return get_default_currency()
    
    location_lower = location.lower().strip()
    if location_lower in COUNTRY_CURRENCY_MAP:
        return COUNTRY_CURRENCY_MAP[location_lower]
    
    for country, currency in COUNTRY_CURRENCY_MAP.items():
        if country in location_lower:
            return currency
    
    return get_default_currency()


def detect_currency_from_profile(profile: dict) -> str:
    """Détecte la devise à partir du profil utilisateur."""
    if "preferred_currency" in profile:
        return profile["preferred_currency"].upper()
    
    location = (
        profile.get("location") or
        profile.get("country") or
        profile.get("city")
    )
    
    if location:
        return detect_currency_from_location(str(location))
    
    return get_default_currency()


def get_default_currency() -> str:
    """Retourne la devise par défaut configurée."""
    return os.getenv("DEFAULT_CURRENCY", "XOF")


def get_currency_from_request(
    request_params: Optional[dict] = None,
    user_profile: Optional[dict] = None
) -> str:
    """Détecte la devise avec priorités: params > profil > env > XOF."""
    if request_params and "currency" in request_params:
        currency = request_params["currency"].upper()
        if is_supported_currency(currency):
            return currency
        logger.warning(f"Devise non supportée: {currency}, fallback défaut")
    
    if user_profile:
        return detect_currency_from_profile(user_profile)
    
    return get_default_currency()


def is_supported_currency(currency_code: str) -> bool:
    """Vérifie si la devise est supportée."""
    return currency_code.upper() in SUPPORTED_CURRENCIES
