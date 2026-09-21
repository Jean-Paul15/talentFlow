"""
Configuration du training et réentraînement.
"""
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration du training."""
    
    # Données d'entraînement
    min_training_samples: int = Field(
        default=100, ge=1,
        description="Nombre minimum d'échantillons pour l'entraînement"
    )
    bootstrap_mode: bool = Field(
        default=True,
        description="Mode bootstrap avec pseudo-labels"
    )
    bootstrap_sample_size: int = Field(
        default=1000, ge=1,
        description="Taille de l'échantillon bootstrap"
    )
    
    # Validation
    validation_split: float = Field(
        default=0.2, ge=0, le=1,
        description="Proportion des données pour la validation"
    )
    early_stopping_rounds: int = Field(
        default=10, ge=1,
        description="Nombre de rounds sans amélioration avant arrêt"
    )
    
    # Réévaluation et retraining
    retraining_frequency_days: int = Field(
        default=7, ge=1,
        description="Fréquence de réentraînement (jours)"
    )
    min_new_samples_for_retrain: int = Field(
        default=50, ge=1,
        description="Minimum de nouveaux échantillons pour réentraîner"
    )
    model_performance_threshold: float = Field(
        default=0.65, ge=0, le=1,
        description="NDCG@10 minimum pour déployer le modèle"
    )
