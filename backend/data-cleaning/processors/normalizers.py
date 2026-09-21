# Normaliseurs de donnees specifiques
# Localisations, pays et types de contrat

from __future__ import annotations

import re
import unicodedata
from typing import Optional


TOGO_CITY_MAP = {
    "lome": "Lome",
    "lomé": "Lome",
    "djidjole": "Lome",
    "djidjolé": "Lome",
    "adidogome": "Lome",
    "adidogomé": "Lome",
    "avenou": "Lome",
    "kara": "Kara",
    "sokode": "Sokode",
    "sokodé": "Sokode",
    "atakpame": "Atakpame",
    "atakpamé": "Atakpame",
    "dapaong": "Dapaong",
    "kpalime": "Kpalime",
    "kpalimé": "Kpalime",
    "tsevie": "Tsevie",
    "tsévié": "Tsevie",
    "aneho": "Aneho",
    "aného": "Aneho",
}

CITY_TO_COUNTRY = {
    "lome": "Togo",
    "kara": "Togo",
    "sokode": "Togo",
    "atakpame": "Togo",
    "dapaong": "Togo",
    "kpalime": "Togo",
    "tsevie": "Togo",
    "aneho": "Togo",
    "dakar": "Senegal",
    "abidjan": "Cote d'Ivoire",
    "yaounde": "Cameroun",
    "cotonou": "Benin",
    "addis abeba": "Ethiopie",
    "addis-abeba": "Ethiopie",
    "geneve": "Suisse",
    "genève": "Suisse",
    "berlin": "Allemagne",
    "paris": "France",
    "libreville": "Gabon",
    "london": "Royaume-Uni",
    "londres": "Royaume-Uni",
    "new york": "USA",
}

COUNTRY_ALIASES = {
    "togo": "Togo",
    "senegal": "Senegal",
    "sénégal": "Senegal",
    "cote d'ivoire": "Cote d'Ivoire",
    "côte d'ivoire": "Cote d'Ivoire",
    "ivory coast": "Cote d'Ivoire",
    "cameroun": "Cameroun",
    "cameroon": "Cameroun",
    "benin": "Benin",
    "bénin": "Benin",
    "gabon": "Gabon",
    "ethiopie": "Ethiopie",
    "ethiopia": "Ethiopie",
    "suisse": "Suisse",
    "switzerland": "Suisse",
    "allemagne": "Allemagne",
    "germany": "Allemagne",
    "france": "France",
    "royaume uni": "Royaume-Uni",
    "united kingdom": "Royaume-Uni",
    "usa": "USA",
    "etats unis": "USA",
    "etats-unis": "USA",
    "united states": "USA",
    "international": "International",
    "remote": "International",
    "worldwide": "International",
    "afrique": "Afrique",
    "africa": "Afrique",
}


def _collapse_spaces(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _fold(value: Optional[str]) -> str:
    normalized = unicodedata.normalize("NFKD", _collapse_spaces(value).lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _title_case_fallback(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def normalize_location(location: Optional[str]) -> str:
    """
    Normalise une localisation.
    """
    cleaned = _collapse_spaces(location)
    if not cleaned:
        return "Non precise"

    lowered = _fold(cleaned)
    if any(token in lowered for token in ("remote", "teletravail", "télétravail", "hybride", "hybrid")):
        return "Remote"
    if lowered in {"international", "worldwide", "global"}:
        return "International"

    for key, value in TOGO_CITY_MAP.items():
        if key in lowered:
            return value

    for city in CITY_TO_COUNTRY:
        if city in lowered:
            return _title_case_fallback(city.replace("-", " "))

    if "togo" in lowered:
        return "Togo"
    if "afrique" in lowered or "africa" in lowered:
        return "Afrique"

    return cleaned


def normalize_contract_type(contract: Optional[str]) -> Optional[str]:
    """
    Normalise le type de contrat.
    """
    cleaned = _collapse_spaces(contract)
    if not cleaned:
        return None

    contract_lower = _fold(cleaned)

    if "contrat a duree indeterminee" in contract_lower or "contrat a duree indetermine" in contract_lower or "cdi" in contract_lower:
        return "CDI"
    if "contrat a duree determinee" in contract_lower or "cdd" in contract_lower:
        return "CDD"
    if "stage" in contract_lower or "intern" in contract_lower:
        return "Stage"
    if "freelance" in contract_lower or "independant" in contract_lower or "independent" in contract_lower:
        return "Freelance"
    if "prestataire" in contract_lower or "prestation" in contract_lower:
        return "Prestataire"
    if "consultant" in contract_lower or "consultance" in contract_lower:
        return "Consultant"
    if "temps plein" in contract_lower or "full-time" in contract_lower or "full time" in contract_lower:
        return "Temps plein"
    if "temps partiel" in contract_lower or "part-time" in contract_lower or "part time" in contract_lower:
        return "Temps partiel"
    if "remote" in contract_lower:
        return "Remote"

    return cleaned


def normalize_country(
    country: Optional[str],
    *,
    location: Optional[str] = None,
    source_name: Optional[str] = None,
) -> str:
    """
    Normalise le pays en s'appuyant sur le champ pays puis sur la location.
    """
    country_clean = _collapse_spaces(country)
    country_folded = _fold(country_clean)
    if country_folded in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[country_folded]

    location_clean = _collapse_spaces(location)
    location_folded = _fold(location_clean)

    if location_clean == "Remote":
        return "International"
    if location_clean == "International":
        return "International"
    if location_clean == "Afrique":
        return "Afrique"

    for alias, normalized in COUNTRY_ALIASES.items():
        if alias and alias in location_folded:
            return normalized

    for city, normalized_country in CITY_TO_COUNTRY.items():
        if city in location_folded:
            return normalized_country

    source_folded = _fold(source_name)
    if source_folded in {"anpe_togo", "emploi_tg", "emploitogo_com", "lucreatif"}:
        return "Togo"
    if source_folded == "wiijob":
        return "Afrique"

    return country_clean or "Non precise"
