"""
Chargement et prédiction du modèle de ranking.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple
import joblib
import numpy as np

from .config import RankingConfig

logger = logging.getLogger(__name__)


def load_model(config: RankingConfig) -> Tuple[Optional[object], Optional[object]]:
    """Charge le modèle ML et le scaler depuis le disque."""
    try:
        model_path = Path("/app/models")
        model_file = model_path / f"ranker_{config.model.model_version}.pkl"
        scaler_file = model_path / f"scaler_{config.model.model_version}.pkl"
        if model_file.exists() and scaler_file.exists():
            model = joblib.load(model_file)
            scaler = joblib.load(scaler_file)
            logger.info(f"Modèle ML chargé: {config.model.model_version}")
            return model, scaler
        logger.warning("Aucun modèle ML trouvé - fallback rule-based")
        return None, None
    except Exception as e:
        logger.error(f"Erreur chargement modèle ML: {e}")
        return None, None


def predict_scores(
    model: object,
    scaler: object,
    features_array: np.ndarray
) -> np.ndarray:
    """Prédit les scores ML avec normalisation."""
    features_scaled = scaler.transform(features_array)
    return model.predict(features_scaled)
