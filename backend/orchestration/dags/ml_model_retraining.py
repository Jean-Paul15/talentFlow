"""
DAG Airflow pour le retraining automatique du modèle ML.
S'exécute hebdomadairement uniquement si nouvelles données disponibles.
Philosophie: event-driven, ne démarre que si nécessaire.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
import httpx

logger = logging.getLogger(__name__)

# Configuration par défaut du DAG
default_args = {
    'owner': 'talentflow-ml',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def check_new_interactions(**context) -> str:
    """
    Vérifie si assez de nouvelles interactions pour retraining.
    Retourne 'train_model' ou 'skip_training'.
    """
    try:
        pg_hook = PostgresHook(postgres_conn_id='talentflow_db')
        
        # Récupération de la dernière date de training
        last_training = pg_hook.get_first(
            """
            SELECT trained_at FROM ml_model_versions
            ORDER BY trained_at DESC LIMIT 1
            """
        )
        
        last_training_date = (
            last_training[0] if last_training
            else datetime.now() - timedelta(days=365)
        )
        
        # Compte des nouvelles interactions
        new_interactions_count = pg_hook.get_first(
            """
            SELECT COUNT(*) FROM user_interactions
            WHERE created_at > %s
            """,
            parameters=(last_training_date,)
        )[0]
        
        logger.info(
            f"Nouvelles interactions depuis dernier training: "
            f"{new_interactions_count}"
        )
        
        # Seuil minimum: 500 nouvelles interactions
        if new_interactions_count >= 500:
            logger.info("Assez de données - démarrage training")
            return 'train_model'
        else:
            logger.info(
                f"Pas assez de données ({new_interactions_count} < 500) - "
                f"skip training"
            )
            return 'skip_training'
    
    except Exception as e:
        logger.error(f"Erreur check interactions: {e}")
        return 'skip_training'


def trigger_model_training(**context) -> dict:
    """
    Déclenche le training du modèle via API recommendation service.
    """
    try:
        # Génération de la version du modèle
        version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Appel API recommendation service
        response = httpx.post(
            "http://recommendation:8003/api/ml/train",
            json={
                "model_version": version,
                "use_gpu": True,
                "days_back": 90
            },
            timeout=3600  # 1h timeout pour training
        )
        
        response.raise_for_status()
        training_result = response.json()
        
        logger.info(f"Training terminé: {training_result}")
        
        # Stockage des métadonnées
        pg_hook = PostgresHook(postgres_conn_id='talentflow_db')
        pg_hook.run(
            """
            INSERT INTO ml_model_versions (
                version, trained_at, training_samples,
                validation_samples, best_score, metrics
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            parameters=(
                version,
                datetime.now(),
                training_result.get('training_samples'),
                training_result.get('validation_samples'),
                training_result.get('best_score', {}).get('val', {}).get('ndcg@10'),
                training_result
            )
        )
        
        return training_result
    
    except Exception as e:
        logger.error(f"Erreur training modèle: {e}")
        raise


def validate_new_model(**context) -> str:
    """
    Valide le nouveau modèle sur un held-out set.
    Compare avec le modèle en production.
    Retourne 'deploy_model' ou 'rollback_model'.
    """
    try:
        ti = context['ti']
        training_result = ti.xcom_pull(task_ids='train_model')
        
        new_version = training_result.get('model_version')
        new_score = training_result.get('best_score', {}).get('val', {}).get('ndcg@10', 0)
        
        # Récupération du score du modèle actuel
        pg_hook = PostgresHook(postgres_conn_id='talentflow_db')
        current_model = pg_hook.get_first(
            """
            SELECT version, best_score FROM ml_model_versions
            WHERE is_production = TRUE
            ORDER BY trained_at DESC LIMIT 1
            """
        )
        
        if current_model:
            current_score = current_model[1]
            improvement = ((new_score - current_score) / current_score) * 100
            
            logger.info(
                f"Nouveau modèle: {new_score:.4f} | "
                f"Actuel: {current_score:.4f} | "
                f"Amélioration: {improvement:.2f}%"
            )
            
            # Déploiement si amélioration >= 2%
            if improvement >= 2.0:
                logger.info("Validation OK - déploiement du nouveau modèle")
                return 'deploy_model'
            else:
                logger.warning(
                    f"Amélioration insuffisante ({improvement:.2f}% < 2%) - "
                    f"rollback"
                )
                return 'rollback_model'
        else:
            # Premier modèle - déploiement automatique
            logger.info("Premier modèle - déploiement automatique")
            return 'deploy_model'
    
    except Exception as e:
        logger.error(f"Erreur validation modèle: {e}")
        return 'rollback_model'


def deploy_model_to_production(**context) -> bool:
    """
    Déploie le nouveau modèle en production.
    """
    try:
        ti = context['ti']
        training_result = ti.xcom_pull(task_ids='train_model')
        new_version = training_result.get('model_version')
        
        # Mise à jour du flag production
        pg_hook = PostgresHook(postgres_conn_id='talentflow_db')
        
        # Désactivation de l'ancien modèle
        pg_hook.run(
            "UPDATE ml_model_versions SET is_production = FALSE"
        )
        
        # Activation du nouveau
        pg_hook.run(
            """
            UPDATE ml_model_versions
            SET is_production = TRUE, deployed_at = %s
            WHERE version = %s
            """,
            parameters=(datetime.now(), new_version)
        )
        
        # Rechargement du modèle dans le service
        response = httpx.post(
            "http://recommendation:8003/api/ml/reload",
            json={"version": new_version},
            timeout=30
        )
        response.raise_for_status()
        
        logger.info(f"Modèle {new_version} déployé en production")
        
        # Envoi de métriques Prometheus
        response = httpx.post(
            "http://prometheus-pushgateway:9091/metrics/job/ml_training",
            data=f"ml_model_deployed{{version=\"{new_version}\"}} 1"
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur déploiement modèle: {e}")
        raise


def rollback_model(**context) -> bool:
    """
    Rollback - conserve le modèle actuel.
    """
    ti = context['ti']
    training_result = ti.xcom_pull(task_ids='train_model')
    failed_version = training_result.get('model_version')
    
    logger.warning(
        f"Rollback du modèle {failed_version} - "
        f"conservation du modèle actuel"
    )
    
    # Marquage du modèle comme rollback
    pg_hook = PostgresHook(postgres_conn_id='talentflow_db')
    pg_hook.run(
        """
        UPDATE ml_model_versions
        SET is_production = FALSE, rollback_reason = %s
        WHERE version = %s
        """,
        parameters=("insufficient_improvement", failed_version)
    )
    
    return True


def send_alert_on_failure(**context) -> bool:
    """
    Envoie une alerte si le training échoue.
    """
    logger.error("Training échoué - envoi d'alerte")
    
    # Envoi de métriques Prometheus
    try:
        response = httpx.post(
            "http://prometheus-pushgateway:9091/metrics/job/ml_training",
            data="ml_training_failed 1"
        )
    except Exception as e:
        logger.error(f"Erreur envoi alerte: {e}")
    
    return True


# Définition du DAG
with DAG(
    'ml_model_retraining',
    default_args=default_args,
    description='Retraining automatique du modèle ML (event-driven)',
    schedule_interval='0 2 * * 0',  # Tous les dimanches à 2h du matin
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['ml', 'recommendation', 'event-driven']
) as dag:
    
    # Vérification des nouvelles données
    check_data = BranchPythonOperator(
        task_id='check_new_interactions',
        python_callable=check_new_interactions,
        provide_context=True
    )
    
    # Training du modèle
    train = PythonOperator(
        task_id='train_model',
        python_callable=trigger_model_training,
        provide_context=True
    )
    
    # Validation du modèle
    validate = BranchPythonOperator(
        task_id='validate_model',
        python_callable=validate_new_model,
        provide_context=True
    )
    
    # Déploiement
    deploy = PythonOperator(
        task_id='deploy_model',
        python_callable=deploy_model_to_production,
        provide_context=True,
        on_failure_callback=send_alert_on_failure
    )
    
    # Rollback
    rollback = PythonOperator(
        task_id='rollback_model',
        python_callable=rollback_model,
        provide_context=True
    )
    
    # Skip (pas assez de données)
    skip = EmptyOperator(
        task_id='skip_training'
    )
    
    # Tâche finale
    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed_min_one_success'
    )
    
    # Pipeline
    check_data >> [train, skip]
    train >> validate >> [deploy, rollback]
    [deploy, rollback, skip] >> end
