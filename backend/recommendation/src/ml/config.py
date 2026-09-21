"""
Configuration complète pour le système de ranking ML.
Agrège toutes les sous-configurations.
"""
from pydantic import BaseModel, Field

from .config_features import FeatureConfig
from .config_thresholds import ThresholdConfig
from .config_model import ModelConfig
from .config_training import TrainingConfig


class CurrencyConfig(BaseModel):
    """Configuration de la devise et localisation."""
    
    default_currency: str = Field(
        default="XOF",
        description="Devise par défaut (ISO 4217: XOF, EUR, USD, etc.)"
    )
    supported_currencies: list[str] = Field(
        default=["XOF", "EUR", "USD", "GBP", "CAD"],
        description="Devises supportées"
    )
    enable_auto_detection: bool = Field(
        default=True,
        description="Activer détection automatique devise (géoloc/profil)"
    )
    enable_currency_conversion: bool = Field(
        default=True,
        description="Activer conversion automatique entre devises"
    )
    conversion_api_url: str = Field(
        default="https://api.frankfurter.app/latest",
        description="API de conversion de devises (gratuite)"
    )


class RankingConfig(BaseModel):
    """Configuration complète du système de ranking."""
    
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    currency: CurrencyConfig = Field(default_factory=CurrencyConfig)
    
    # Chemins de sauvegarde
    model_path: str = Field(
        default="/app/models/ranker",
        description="Chemin de sauvegarde du modèle"
    )
    feature_names_path: str = Field(
        default="/app/models/feature_names.json",
        description="Chemin des noms de features"
    )
    
    # Configuration Redis pour le cache
    redis_cache_ttl: int = Field(
        default=3600, ge=0,
        description="TTL du cache Redis (secondes)"
    )
    redis_cache_key_prefix: str = Field(
        default="ml_rank:",
        description="Préfixe des clés Redis"
    )
    enable_caching: bool = Field(
        default=True,
        description="Activer le système de cache Redis"
    )
    
    # GPU/CPU Configuration
    prefer_gpu: bool = Field(
        default=True,
        description="Préférer GPU si disponible (fallback CPU auto)"
    )
    gpu_device_id: int = Field(
        default=0,
        description="ID du device GPU à utiliser"
    )
    
    # Pool de candidats adaptatif (conservé pour compatibilité)
    candidate_pool_ratio: float = Field(
        default=0.10,
        description="Ratio du pool de candidats par rapport au total"
    )
    min_candidate_pool: int = Field(
        default=50,
        description="Taille minimum du pool de candidats"
    )
    max_candidate_pool: int = Field(
        default=500,
        description="Taille maximum du pool de candidats"
    )
