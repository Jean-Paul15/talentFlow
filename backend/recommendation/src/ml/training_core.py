"""
Pipeline de training pour le modèle LightGBM.
"""
import logging
from typing import Dict, Any, Tuple
import numpy as np
import asyncpg

from .training_data import collect_training_data
from .training_labels import generate_labels
from .training_features import extract_features_from_row, FEATURE_NAMES
from .training_runner import train_lightgbm_model

logger = logging.getLogger(__name__)


class ModelTrainingPipeline:
    """Pipeline complet de training du modèle LightGBM."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.feature_names = FEATURE_NAMES
    
    async def train_model(
        self,
        model_version: str = "v1.0.0",
        use_gpu: bool = True,
        days_back: int = 90
    ) -> Tuple[bool, Dict[str, Any]]:
        """Entraîne le modèle LightGBM avec GPU si disponible."""
        try:
            logger.info("Collecte des données de training...")
            df = await collect_training_data(self.db_pool, days_back)
            if len(df) < 500:
                logger.warning(
                    f"Pas assez de données pour training: {len(df)} < 500"
                )
                return False, {"error": "insufficient_data", "count": len(df)}
            logger.info("Génération des labels...")
            y = generate_labels(df)
            logger.info("Extraction des features...")
            X = np.array([
                extract_features_from_row(row)
                for _, row in df.iterrows()
            ])
            return train_lightgbm_model(
                X, y, self.feature_names, model_version, use_gpu
            )
        except Exception as e:
            logger.error(f"Erreur training modèle: {e}")
            return False, {"error": str(e)}
