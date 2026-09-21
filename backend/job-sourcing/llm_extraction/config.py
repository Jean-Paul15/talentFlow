# Configuration du module LLM
# Mode officiel: Gemini uniquement avec fallback par seconde cle

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from loguru import logger


@dataclass
class LLMConfig:
    """
    Configuration Gemini-only pour l'enrichissement des offres.

    Variables d'environnement supportees:
        LLM_ENABLED                 : "true" ou "false"
        GEMINI_API_KEY              : cle principale
        GEMINI_API_KEY_FALLBACK     : cle secondaire
        GEMINI_API_KEYS             : liste CSV optionnelle de cles
        GEMINI_MODEL                : modele principal
        GEMINI_MODEL_PRIORITY       : liste CSV optionnelle de modeles
        GEMINI_BASE_URL             : URL API Gemini
        LLM_MAX_TOKENS              : limite de sortie
        LLM_TEMPERATURE             : temperature
    """

    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_key: str = ""
    api_keys: List[str] = field(default_factory=list)
    model_priority: List[str] = field(default_factory=list)
    enabled: bool = False
    max_tokens: int = 500
    temperature: float = 0.1
    prompts: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        enabled = os.getenv("LLM_ENABLED", "false").strip().lower() == "true"
        if not enabled:
            logger.info("LLM desactive (LLM_ENABLED=false)")
            return cls(enabled=False, prompts=DEFAULT_PROMPTS.copy())

        api_keys = _collect_gemini_api_keys()
        if not api_keys:
            logger.warning("LLM active mais aucune cle Gemini n'est configuree")
            return cls(enabled=False, prompts=DEFAULT_PROMPTS.copy())

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        model_priority = _csv_env(
            "GEMINI_MODEL_PRIORITY",
            [model, "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        )

        config = cls(
            provider="gemini",
            model=model,
            base_url=os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            ).strip()
            or "https://generativelanguage.googleapis.com/v1beta",
            api_key=api_keys[0],
            api_keys=api_keys,
            model_priority=model_priority,
            enabled=True,
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            prompts=DEFAULT_PROMPTS.copy(),
        )

        logger.info(
            "LLM configure: provider=gemini, model={}, keys={}, url={}",
            config.model,
            len(config.api_keys),
            config.base_url,
        )
        return config


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items or list(default)


def _collect_gemini_api_keys() -> List[str]:
    values: List[str] = []
    for key in (
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GEMINI_API_KEY_FALLBACK", ""),
    ):
        key = key.strip()
        if key and key not in values:
            values.append(key)

    extra = os.getenv("GEMINI_API_KEYS", "")
    for key in extra.split(","):
        normalized = key.strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


DEFAULT_PROMPTS = {
    "extract_structured": """Tu es un expert en extraction de donnees d'offres d'emploi.
Extrais les informations suivantes du texte fourni et retourne un JSON strict :
{{
    "title": "titre du poste",
    "company": "nom de l'entreprise",
    "location": "lieu de travail",
    "contract_type": "CDI/CDD/Stage/Freelance/...",
    "salary": "salaire si mentionne",
    "experience": "experience requise",
    "education": "niveau d'etude requis",
    "skills": ["competence1", "competence2"],
    "sector": "secteur d'activite",
    "deadline": "date limite de candidature",
    "contact_email": "email de contact",
    "contact_phone": "telephone de contact"
}}
Mets null pour les champs non trouves. Ne fabrique rien.""",
    "classify_sector": """Classe cette offre d'emploi dans UN des secteurs suivants :
- informatique_tech
- finance_comptabilite
- marketing_communication
- sante_medical
- education_formation
- construction_btp
- agriculture
- commerce_vente
- logistique_transport
- administration_rh
- juridique
- hotellerie_restauration
- ong_humanitaire
- autre

Reponds uniquement par le nom du secteur, rien d'autre.""",
    "extract_skills": """Extrais toutes les competences techniques et non-techniques
mentionnees dans cette offre d'emploi. Retourne une liste JSON :
["competence1", "competence2", ...]
Inclus : langages de programmation, outils, logiciels, langues, soft skills.
Ne fabrique pas de competences non mentionnees.""",
    "summarize": """Resume cette offre d'emploi en 3 phrases maximum.
Mentionne : le poste, l'entreprise, la localisation et les exigences cles.""",
}
