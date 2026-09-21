# DAG Airflow pour l'Etape 2: Nettoyage et Enrichissement
# Orchestre le pipeline Bronze -> Silver

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup


# Arguments par defaut du DAG
default_args = {
    "owner": "talentflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def run_cleaning_pipeline(**context):
    """
    Execute le pipeline de nettoyage.
    """
    import sys
    sys.path.insert(0, "/opt/airflow/data-cleaning")
    
    from pipeline import CleaningPipeline
    from datetime import datetime, timedelta
    
    # Recuperer le contexte d'execution
    execution_date = context["execution_date"]
    since_date = execution_date - timedelta(hours=6)
    
    # Executer le pipeline
    pipeline = CleaningPipeline()
    stats = pipeline.run(since_date=since_date)
    
    # Pousser les stats pour le monitoring
    context["ti"].xcom_push(key="pipeline_stats", value=stats)
    
    return stats


def validate_results(**context):
    """
    Valide les resultats du pipeline.
    """
    stats = context["ti"].xcom_pull(
        task_ids="cleaning_pipeline.run_pipeline",
        key="pipeline_stats"
    )
    
    if not stats:
        raise ValueError("Pas de stats disponibles")
    
    error_rate = stats.get("errors", 0) / max(stats.get("processed", 1), 1)
    
    if error_rate > 0.1:
        raise ValueError(f"Taux d'erreur trop eleve: {error_rate:.1%}")
    
    return f"Validation OK: {stats['stored']} offres stockees"


# DAG principal
with DAG(
    dag_id="etape2_cleaning_enrichment",
    default_args=default_args,
    description="Pipeline de nettoyage et enrichissement des offres",
    schedule_interval="15 0,3,13,18,21 * * *",  # mini-midi + fenetre longue nuit
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["talentflow", "etape2", "cleaning", "enrichment"],
) as dag:
    
    # Groupe de taches pour le pipeline
    with TaskGroup(group_id="cleaning_pipeline") as cleaning_group:
        
        run_pipeline = PythonOperator(
            task_id="run_pipeline",
            python_callable=run_cleaning_pipeline,
            provide_context=True,
        )
        
        validate = PythonOperator(
            task_id="validate_results",
            python_callable=validate_results,
            provide_context=True,
        )
        
        run_pipeline >> validate
    
    # Notification de fin (optionnel)
    notify_completion = BashOperator(
        task_id="notify_completion",
        bash_command='echo "Pipeline Etape 2 termine a $(date)"',
    )
    
    cleaning_group >> notify_completion
