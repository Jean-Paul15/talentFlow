"""
Configuration des features pour le système de ranking ML.
"""
from pydantic import BaseModel, Field


class FeatureConfig(BaseModel):
    """Configuration des features pour le ranking."""
    
    # Features sémantiques
    semantic_weight: float = Field(
        default=0.35, ge=0, le=1,
        description="Poids du score sémantique"
    )
    skill_overlap_weight: float = Field(
        default=0.25, ge=0, le=1,
        description="Poids du chevauchement de compétences"
    )
    
    # Features d'expérience
    experience_match_weight: float = Field(
        default=0.15, ge=0, le=1,
        description="Poids de la correspondance d'expérience"
    )
    seniority_match_weight: float = Field(
        default=0.10, ge=0, le=1,
        description="Poids du niveau de séniorité"
    )
    
    # Features géographiques et contextuelles
    location_score_weight: float = Field(
        default=0.08, ge=0, le=1,
        description="Poids du score de localisation"
    )
    remote_compatibility_weight: float = Field(
        default=0.05, ge=0, le=1,
        description="Poids de la compatibilité remote"
    )
    
    # Features de qualité de l'offre (OPTIONNELLES avec fallback 0.5)
    company_reputation_weight: float = Field(
        default=0.12, ge=0, le=1,
        description="Poids réputation entreprise (0.5 si donnée manquante)"
    )
    offer_freshness_weight: float = Field(
        default=0.08, ge=0, le=1,
        description="Poids de la fraîcheur de l'offre"
    )
    application_rate_weight: float = Field(
        default=0.05, ge=0, le=1,
        description="Poids taux candidature (0.5 si donnée manquante)"
    )
    salary_match_weight: float = Field(
        default=0.08, ge=0, le=1,
        description="Poids match salarial (0.5 si donnée manquante)"
    )
    contract_type_weight: float = Field(
        default=0.04, ge=0, le=1,
        description="Poids type contrat (0.5 si donnée manquante)"
    )
    
    # Features de diversité
    enable_diversity_boost: bool = Field(
        default=True,
        description="Activer le boost de diversité"
    )
    diversity_threshold: float = Field(
        default=0.85, ge=0, le=1,
        description="Seuil de similarité pour la diversité"
    )
    diversity_penalty: float = Field(
        default=0.8, ge=0, le=1,
        description="Pénalité appliquée aux doublons d'entreprise"
    )
    company_repeat_limit: int = Field(
        default=3, ge=1,
        description="Maximum d'offres par entreprise dans le top"
    )
    freshness_boost_days: int = Field(
        default=7, ge=1,
        description="Boost pour offres publiées récemment (jours)"
    )
    old_job_penalty_days: int = Field(
        default=60, ge=1,
        description="Pénalité pour offres anciennes (jours)"
    )
