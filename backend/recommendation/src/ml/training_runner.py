"""
Entraînement LightGBM et sauvegarde du modèle.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib


def train_lightgbm_model(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list,
    model_version: str,
    use_gpu: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """Entraîne LightGBM et sauvegarde le modèle."""
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    lgb_params = {
        'objective': 'lambdarank',
        'metric': 'ndcg',
        'ndcg_eval_at': [5, 10, 20],
        'learning_rate': 0.05,
        'num_leaves': 31,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1
    }
    if use_gpu:
        lgb_params['device'] = 'gpu'
        lgb_params['gpu_platform_id'] = 0
        lgb_params['gpu_device_id'] = 0
    train_data = lgb.Dataset(
        X_train_scaled,
        label=y_train,
        feature_name=feature_names
    )
    val_data = lgb.Dataset(
        X_val_scaled,
        label=y_val,
        feature_name=feature_names,
        reference=train_data
    )
    model = lgb.train(
        lgb_params,
        train_data,
        num_boost_round=500,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'val'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=50)
        ]
    )
    model_dir = Path("/app/models")
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / f"ranker_{model_version}.pkl"
    scaler_path = model_dir / f"scaler_{model_version}.pkl"
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    metrics = {
        "model_version": model_version,
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "best_iteration": model.best_iteration,
        "best_score": model.best_score,
        "trained_at": datetime.now().isoformat(),
        "gpu_used": use_gpu
    }
    return True, metrics
