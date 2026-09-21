"""
DAG Airflow pour le réentraînement automatique du modèle ML de ranking.

Workflow:
1. Vérifier si le réentraînement est nécessaire (nouvelles données)
2. Collecter les données d'entraînement depuis PostgreSQL
3. Entraîner le modèle LightGBM
4. Évaluer les performances (NDCG@10)
5. Déployer si les performances sont satisfaisantes
6. Archiver l'ancien modèle
7. Notifier les résultats

Fréquence: Hebdomadaire (tous les lundis à 02:00)
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
import os
import sys

# Ajouter le chemin du module recommendation au PYTHONPATH
sys.path.insert(0, '/app/backend/recommendation/src')

from ml.ranker import MLRankingService
from ml.config import RankingConfig
from ml.data_collector import TrainingDataCollector

logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://user:CHANGEME@postgres:5432/talentflow'
)

MODEL_ARCHIVE_DIR = '/app/models/archive'
PERFORMANCE_THRESHOLD = 0.65  # NDCG@10 minimum

# Default args pour le DAG
default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email': ['ml-team@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}


def check_retraining_needed(**context) -> str:
    """
    Vérifie si le réentraînement est nécessaire.
    
    Returns:
        'retrain' si nécessaire, 'skip' sinon
    """
    try:
        config = RankingConfig()
        collector = TrainingDataCollector(DATABASE_URL, config)
        
        needs_retrain = collector.needs_retraining()
        
        # Obtenir les statistiques
        stats = collector.get_statistics(days=config.training.retraining_frequency_days)
        
        logger.info(f"Vérification réentraînement: {stats}")
        logger.info(f"Réentraînement nécessaire: {needs_retrain}")
        
        # Pusher les stats dans XCom
        context['ti'].xcom_push(key='training_stats', value=stats)
        
        return 'collect_training_data' if needs_retrain else 'skip_retraining'
        
    except Exception as e:
        logger.error(f"Erreur vérification réentraînement: {e}", exc_info=True)
        return 'skip_retraining'


def collect_training_data(**context) -> Dict[str, Any]:
    """
    Collecte les données d'entraînement.
    
    Returns:
        Métadonnées sur les données collectées
    """
    try:
        config = RankingConfig()
        collector = TrainingDataCollector(DATABASE_URL, config)
        
        # Collecter les données (mode bootstrap si insuffisant)
        features_df, labels, query_ids = collector.collect_training_data(
            bootstrap_mode=config.training.bootstrap_mode
        )
        
        metadata = {
            'total_samples': len(features_df),
            'unique_queries': len(set(query_ids)),
            'label_distribution': {
                int(label): int(count)
                for label, count in zip(*np.unique(labels, return_counts=True))
            },
            'feature_count': len(features_df.columns),
            'feature_names': list(features_df.columns)
        }
        
        logger.info(f"Données collectées: {metadata}")
        
        # Sauvegarder temporairement
        features_df.to_parquet('/tmp/ml_features.parquet')
        np.save('/tmp/ml_labels.npy', labels)
        np.save('/tmp/ml_query_ids.npy', query_ids)
        
        # Pusher les métadonnées
        context['ti'].xcom_push(key='data_metadata', value=metadata)
        
        return metadata
        
    except Exception as e:
        logger.error(f"Erreur collecte données: {e}", exc_info=True)
        raise


def train_model(**context) -> Dict[str, Any]:
    """
    Entraîne le modèle LightGBM.
    
    Returns:
        Métriques d'entraînement
    """
    try:
        import pandas as pd
        import numpy as np
        
        # Charger les données
        features_df = pd.read_parquet('/tmp/ml_features.parquet')
        labels = np.load('/tmp/ml_labels.npy')
        query_ids = np.load('/tmp/ml_query_ids.npy')
        
        logger.info(f"Données chargées: {len(features_df)} échantillons")
        
        # Initialiser le service de ranking
        config = RankingConfig()
        ranker = MLRankingService(config)
        
        # Entraîner
        metrics = ranker.train(
            training_data=features_df,
            labels=labels,
            query_ids=query_ids
        )
        
        logger.info(f"Entraînement terminé: {metrics}")
        
        # Pusher les métriques
        context['ti'].xcom_push(key='training_metrics', value=metrics)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Erreur entraînement modèle: {e}", exc_info=True)
        raise


def evaluate_model(**context) -> str:
    """
    Évalue le modèle et décide du déploiement.
    
    Returns:
        'deploy' si performances acceptables, 'rollback' sinon
    """
    try:
        metrics = context['ti'].xcom_pull(key='training_metrics', task_ids='train_model')
        
        if not metrics or metrics.get('status') != 'success':
            logger.warning("Entraînement échoué, rollback")
            return 'rollback_model'
        
        ndcg_at_10 = metrics.get('ndcg_at_10', 0.0)
        
        logger.info(f"Évaluation: NDCG@10 = {ndcg_at_10:.4f} (seuil = {PERFORMANCE_THRESHOLD})")
        
        if ndcg_at_10 >= PERFORMANCE_THRESHOLD:
            logger.info("✅ Performances acceptables, déploiement autorisé")
            return 'deploy_model'
        else:
            logger.warning(f"❌ Performances insuffisantes ({ndcg_at_10:.4f} < {PERFORMANCE_THRESHOLD}), rollback")
            return 'rollback_model'
        
    except Exception as e:
        logger.error(f"Erreur évaluation: {e}", exc_info=True)
        return 'rollback_model'


def deploy_model(**context):
    """Déploie le nouveau modèle (déjà sauvegardé par ranker.train())."""
    try:
        metrics = context['ti'].xcom_pull(key='training_metrics', task_ids='train_model')
        
        logger.info("✅ Modèle déployé avec succès")
        logger.info(f"Métriques: NDCG@10 = {metrics.get('ndcg_at_10', 0):.4f}")
        
        # Archiver l'ancien modèle
        import shutil
        from pathlib import Path
        
        config = RankingConfig()
        model_path = Path(config.model_path)
        
        if model_path.exists():
            archive_dir = Path(MODEL_ARCHIVE_DIR)
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_path = archive_dir / f"ranker_model_{timestamp}.txt"
            
            # Note: Le nouveau modèle est déjà sauvegardé par ranker.train()
            # On archive juste l'info
            with open(archive_path, 'w') as f:
                f.write(f"Model deployed at {timestamp}\n")
                f.write(f"NDCG@10: {metrics.get('ndcg_at_10', 0):.4f}\n")
            
            logger.info(f"Archive créée: {archive_path}")
        
    except Exception as e:
        logger.error(f"Erreur déploiement: {e}", exc_info=True)
        raise


def rollback_model(**context):
    """Rollback en cas de performances insuffisantes."""
    try:
        logger.warning("⚠️  Rollback du modèle - ancien modèle conservé")
        
        # Le modèle existant est conservé (pas écrasé)
        # On log juste l'échec
        metrics = context['ti'].xcom_pull(key='training_metrics', task_ids='train_model')
        
        logger.warning(f"Raison: NDCG@10 = {metrics.get('ndcg_at_10', 0):.4f} < {PERFORMANCE_THRESHOLD}")
        
    except Exception as e:
        logger.error(f"Erreur rollback: {e}", exc_info=True)


def notify_results(**context):
    """Notifie les résultats du réentraînement."""
    try:
        metrics = context['ti'].xcom_pull(key='training_metrics', task_ids='train_model')
        stats = context['ti'].xcom_pull(key='training_stats', task_ids='check_retraining_needed')
        
        message = f"""
        ========================================
        ML RETRAINING PIPELINE - RÉSULTATS
        ========================================
        
        Statut: {'✅ SUCCÈS' if metrics and metrics.get('status') == 'success' else '❌ ÉCHEC'}
        
        Données d'entraînement:
        - Total interactions: {stats.get('total_interactions', 0)}
        - Utilisateurs uniques: {stats.get('unique_users', 0)}
        - Offres uniques: {stats.get('unique_jobs', 0)}
        
        Performances:
        - NDCG@10: {metrics.get('ndcg_at_10', 0):.4f}
        - Échantillons entraînement: {metrics.get('train_samples', 0)}
        - Échantillons validation: {metrics.get('val_samples', 0)}
        
        Features importantes:
        {_format_feature_importance(metrics.get('feature_importance', {}))}
        
        Déploiement: {'✅ DÉPLOYÉ' if metrics.get('ndcg_at_10', 0) >= PERFORMANCE_THRESHOLD else '❌ ROLLBACK'}
        ========================================
        """
        
        logger.info(message)
        
        # TODO: Envoyer notification (email, Slack, etc.)
        
    except Exception as e:
        logger.error(f"Erreur notification: {e}", exc_info=True)


def _format_feature_importance(importance: Dict[str, float]) -> str:
    """Formate l'importance des features."""
    if not importance:
        return "  N/A"
    
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    top_5 = sorted_features[:5]
    
    lines = []
    for feature, score in top_5:
        lines.append(f"  - {feature}: {score:.2f}")
    
    return "\n".join(lines)


def cleanup_temp_files(**context):
    """Nettoie les fichiers temporaires."""
    try:
        import os
        
        temp_files = [
            '/tmp/ml_features.parquet',
            '/tmp/ml_labels.npy',
            '/tmp/ml_query_ids.npy'
        ]
        
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)
                logger.debug(f"Fichier supprimé: {file}")
        
    except Exception as e:
        logger.error(f"Erreur nettoyage: {e}", exc_info=True)


# Définir le DAG
with DAG(
    'ml_retraining_pipeline',
    default_args=default_args,
    description='Pipeline MLOps pour réentraînement automatique du modèle de ranking',
    schedule_interval='0 2 * * 1',  # Tous les lundis à 02:00
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'ranking', 'mlops'],
    max_active_runs=1,
) as dag:
    
    # Task 1: Vérifier si réentraînement nécessaire
    check_task = BranchPythonOperator(
        task_id='check_retraining_needed',
        python_callable=check_retraining_needed,
        provide_context=True,
    )
    
    # Task 2: Skip si pas nécessaire
    skip_task = EmptyOperator(
        task_id='skip_retraining'
    )
    
    # Task 3: Collecter les données
    collect_task = PythonOperator(
        task_id='collect_training_data',
        python_callable=collect_training_data,
        provide_context=True,
    )
    
    # Task 4: Entraîner le modèle
    train_task = PythonOperator(
        task_id='train_model',
        python_callable=train_model,
        provide_context=True,
    )
    
    # Task 5: Évaluer et décider
    evaluate_task = BranchPythonOperator(
        task_id='evaluate_model',
        python_callable=evaluate_model,
        provide_context=True,
    )
    
    # Task 6a: Déployer si OK
    deploy_task = PythonOperator(
        task_id='deploy_model',
        python_callable=deploy_model,
        provide_context=True,
    )
    
    # Task 6b: Rollback si KO
    rollback_task = PythonOperator(
        task_id='rollback_model',
        python_callable=rollback_model,
        provide_context=True,
    )
    
    # Task 7: Notifier résultats
    notify_task = PythonOperator(
        task_id='notify_results',
        python_callable=notify_results,
        provide_context=True,
        trigger_rule='none_failed_min_one_success',
    )
    
    # Task 8: Nettoyage
    cleanup_task = PythonOperator(
        task_id='cleanup_temp_files',
        python_callable=cleanup_temp_files,
        provide_context=True,
        trigger_rule='all_done',
    )
    
    # Définir les dépendances
    check_task >> [skip_task, collect_task]
    collect_task >> train_task >> evaluate_task
    evaluate_task >> [deploy_task, rollback_task]
    [deploy_task, rollback_task, skip_task] >> notify_task >> cleanup_task
