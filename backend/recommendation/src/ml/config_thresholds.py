"""
Configuration des seuils dynamiques pour le ranking ML.
"""
from pydantic import BaseModel, Field


class ThresholdConfig(BaseModel):
    """Configuration des seuils dynamiques."""
    
    # Seuils de base
    min_score: float = Field(
        default=0.40, ge=0, le=1,
        description="Score minimum absolu"
    )
    percentile_threshold: int = Field(
        default=75, ge=0, le=100,
        description="Percentile pour le seuil adaptatif (P75)"
    )
    
    # Adaptation dynamique du top_k
    enable_dynamic_topk: bool = Field(
        default=True,
        description="Activer le top_k dynamique"
    )
    topk_ratio: float = Field(
        default=0.10, ge=0, le=1,
        description="Ratio du total d'offres pour le top_k"
    )
    topk_min: int = Field(
        default=50, ge=1,
        description="Top_k minimum"
    )
    topk_max: int = Field(
        default=200, ge=1,
        description="Top_k maximum"
    )
    
    # Nombre final de recommandations
    min_recommendations: int = Field(
        default=5, ge=1,
        description="Nombre minimum de recommandations"
    )
    max_recommendations: int = Field(
        default=20, ge=1,
        description="Nombre maximum de recommandations"
    )
    target_recommendations: int = Field(
        default=10, ge=1,
        description="Nombre cible de recommandations"
    )
