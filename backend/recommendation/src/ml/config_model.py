"""
Configuration du modèle LightGBM.
"""
from typing import List
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration du modèle LightGBM."""
    
    # Paramètres d'apprentissage
    objective: str = Field(
        default="lambdarank",
        description="Fonction objectif (lambdarank pour learning-to-rank)"
    )
    model_version: str = Field(
        default="v1.0.0",
        description="Version actuelle du modèle ML"
    )
    metric: str = Field(
        default="ndcg",
        description="Métrique d'évaluation"
    )
    ndcg_eval_at: List[int] = Field(
        default=[5, 10, 20],
        description="Positions pour l'évaluation NDCG"
    )
    
    # Hyperparamètres du modèle
    num_leaves: int = Field(
        default=31, ge=2,
        description="Nombre de feuilles par arbre"
    )
    max_depth: int = Field(
        default=6, ge=1,
        description="Profondeur maximale des arbres"
    )
    learning_rate: float = Field(
        default=0.05, ge=0, le=1,
        description="Taux d'apprentissage"
    )
    n_estimators: int = Field(
        default=100, ge=1,
        description="Nombre d'arbres"
    )
    
    # Régularisation
    min_child_samples: int = Field(
        default=20, ge=1,
        description="Nombre minimum d'échantillons par feuille"
    )
    reg_alpha: float = Field(
        default=0.1, ge=0,
        description="Régularisation L1"
    )
    reg_lambda: float = Field(
        default=0.1, ge=0,
        description="Régularisation L2"
    )
    
    # Performance
    n_jobs: int = Field(
        default=-1,
        description="Nombre de threads (-1 pour tous)"
    )
    verbose: int = Field(
        default=-1,
        description="Niveau de verbosité (-1 pour silencieux)"
    )
