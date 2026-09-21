# DAG Airflow principal - Pipeline Big Data
# Flux:
#   1) Job Sourcing publie vers Kafka
#   2) Spark Structured Streaming consomme Kafka et ecrit Bronze MinIO
#   3) Data Cleaning lit Bronze et alimente Silver

import os
import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.utils.trigger_rule import TriggerRule
import requests


JOB_SOURCING_URL = os.getenv("JOB_SOURCING_URL", "http://job-sourcing:8000")
DATA_CLEANING_URL = os.getenv("DATA_CLEANING_URL", "http://data-cleaning:8000")
SEARCH_ENGINE_URL = os.getenv("SEARCH_ENGINE_URL", "http://search-engine:8002")
SEARCH_ENGINE_REQUIRED = str(os.getenv("SEARCH_ENGINE_REQUIRED", "false")).strip().lower() in {"1", "true", "yes", "on"}
SCRAPE_AUTOPILOT_ENABLED = str(os.getenv("SCRAPE_AUTOPILOT_ENABLED", "true")).strip().lower() in {"1", "true", "yes", "on"}
SCRAPE_AUTOPILOT_MAX_TARGETS = int(os.getenv("SCRAPE_AUTOPILOT_MAX_TARGETS", "4"))
SCRAPE_AUTOPILOT_FORCE = str(os.getenv("SCRAPE_AUTOPILOT_FORCE", "false")).strip().lower() in {"1", "true", "yes", "on"}

default_args = {
    "owner": "talentflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _request_json(method: str, url: str, timeout: int = 30, payload=None):
    resp = requests.request(method, url, json=payload, timeout=timeout)
    if resp.status_code >= 300:
        raise RuntimeError(f"HTTP {resp.status_code} on {url}: {resp.text}")
    return resp.json()


def snapshot_bronze_before(**context):
    """Capture le nombre d'objets Bronze avant ingestion."""
    stats = _request_json("GET", f"{JOB_SOURCING_URL}/api/stats", timeout=20)
    bronze = stats.get("minio", {}).get("bronze_objects", 0)
    context["ti"].xcom_push(key="bronze_before", value=bronze)
    return bronze


def scrape_jobs_to_kafka(**context):
    """Declenche le scraping; la sortie est publiee dans Kafka."""
    if SCRAPE_AUTOPILOT_ENABLED:
        result = _request_json(
            "POST",
            (
                f"{JOB_SOURCING_URL}/api/scrape/autopilot/run"
                f"?background=true&max_targets={SCRAPE_AUTOPILOT_MAX_TARGETS}"
                f"&force={'true' if SCRAPE_AUTOPILOT_FORCE else 'false'}"
            ),
            timeout=120,
        )
    else:
        payload = {"full": False}
        result = _request_json(
            "POST",
            f"{JOB_SOURCING_URL}/api/scrape",
            timeout=3600,
            payload=payload,
        )
    produced = (
        result.get("executed_count")
        or result.get("count")
        or len(result.get("job_ids") or [])
        or 0
    )
    context["ti"].xcom_push(key="scraped_count", value=produced)
    context["ti"].xcom_push(key="scrape_execution", value=result)
    return produced


def wait_for_spark_ingestion(**context):
    """
    Attend que Spark ait ecrit de nouveaux objets dans MinIO Bronze.
    On valide au moins +1 objet vs snapshot initial.
    """
    ti = context["ti"]
    scraped_count = ti.xcom_pull(task_ids="scrape_jobs_to_kafka", key="scraped_count")
    try:
        scraped_count_int = int(scraped_count or 0)
    except Exception:
        scraped_count_int = 0
    if scraped_count_int <= 0:
        skipped = {
            "bronze_before": ti.xcom_pull(task_ids="snapshot_bronze_before", key="bronze_before") or 0,
            "bronze_after": None,
            "delta": 0,
            "skipped": True,
            "reason": "no_due_sources_or_no_new_items",
        }
        ti.xcom_push(key="bronze_after", value=skipped["bronze_before"])
        return skipped

    bronze_before = ti.xcom_pull(task_ids="snapshot_bronze_before", key="bronze_before")
    if bronze_before is None:
        bronze_before = 0

    timeout_seconds = 20 * 60
    poll_interval = 20
    elapsed = 0

    while elapsed <= timeout_seconds:
        stats = _request_json("GET", f"{JOB_SOURCING_URL}/api/stats", timeout=20)
        bronze_now = stats.get("minio", {}).get("bronze_objects", 0)
        if bronze_now > bronze_before:
            ti.xcom_push(key="bronze_after", value=bronze_now)
            return {
                "bronze_before": bronze_before,
                "bronze_after": bronze_now,
                "delta": bronze_now - bronze_before,
            }

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        "Aucun nouvel objet Bronze detecte apres ingestion Kafka/Spark"
    )


def run_cleaning_from_bronze(**context):
    """Lance le nettoyage sur les donnees Bronze fraichement ingerees."""
    ingestion = context["ti"].xcom_pull(task_ids="wait_for_spark_ingestion") or {}
    if ingestion.get("skipped") or int(ingestion.get("delta", 0) or 0) <= 0:
        return {
            "cleaned_count": 0,
            "errors": 0,
            "skipped_count": 0,
            "silver_before": None,
            "silver_after": None,
            "silver_delta_count": 0,
            "skipped": True,
            "reason": ingestion.get("reason", "no_new_bronze"),
        }
    before = _request_json("GET", f"{DATA_CLEANING_URL}/api/status", timeout=20)
    silver_before = int(before.get("jobs_in_mongodb", 0) or 0)
    payload = {"since_hours": 168, "full": True}
    result = _request_json(
        "POST",
        f"{DATA_CLEANING_URL}/api/clean",
        timeout=3600,
        payload=payload,
    )
    after = _request_json("GET", f"{DATA_CLEANING_URL}/api/status", timeout=20)
    silver_after = int(after.get("jobs_in_mongodb", 0) or 0)
    return {
        "cleaned_count": result.get("cleaned_count", 0),
        "errors": result.get("errors", 0),
        "skipped_count": result.get("skipped_count", 0),
        "silver_before": silver_before,
        "silver_after": silver_after,
        "silver_delta_count": max(0, silver_after - silver_before),
    }


def ensure_search_index_ready(**context):
    """
    Crée l'index/collection du moteur de recherche si absent.
    Supporte ES ou Qdrant selon le backend actif du search-engine.
    """
    try:
        return _request_json(
            "POST",
            f"{SEARCH_ENGINE_URL}/index/create?force=false",
            timeout=120,
        )
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}


def refresh_search_embeddings_index(**context):
    """
    Relance l'indexation (embeddings + index) depuis Mongo Silver.
    Utilise le backend actif du search-engine.
    """
    # Force=false pour rester idempotent et éviter des recreates inutiles.
    try:
        result = _request_json(
            "POST",
            f"{SEARCH_ENGINE_URL}/index/reindex?force=false",
            timeout=7200,
        )
        return result
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}


def decide_search_reindex_needed(**context):
    """
    Décide s'il faut reindexer le moteur de recherche.
    Règles:
    - si cleaning a produit >0 objets -> reindex
    - sinon vérifier la dérive via /index/sync-status
    """
    ti = context["ti"]
    cleaning = ti.xcom_pull(task_ids="run_cleaning_from_bronze") or {}
    cleaned_count = int(cleaning.get("cleaned_count", 0) or 0)
    if cleaned_count > 0:
        ti.xcom_push(key="search_reindex_decision", value={"run": True, "reason": "cleaning_output"})
        return True

    try:
        status = _request_json("GET", f"{SEARCH_ENGINE_URL}/index/sync-status", timeout=30)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        ti.xcom_push(
            key="search_reindex_decision",
            value={"run": False, "reason": f"search_engine_unavailable: {err}"},
        )
        return False
    run = bool(status.get("needs_reindex", False))
    ti.xcom_push(
        key="search_reindex_decision",
        value={
            "run": run,
            "reason": status.get("reason", "unknown"),
            "drift_count": status.get("drift_count"),
            "drift_ratio": status.get("drift_ratio"),
        },
    )
    return run


def validate_search_index(**context):
    """
    Validation minimale post-indexation: backend actif joignable + index/collection present.
    """
    health = _request_json("GET", f"{SEARCH_ENGINE_URL}/health", timeout=30)
    if health.get("status") == "unhealthy" and not SEARCH_ENGINE_REQUIRED:
        return {"skipped": True, "reason": "search_engine_unavailable"}
    if health.get("status") not in ("healthy", "degraded"):
        raise RuntimeError(f"Search-engine unhealthy: {health}")
    if not health.get("index_exists"):
        raise RuntimeError(f"Index/collection absent apres sync: {health}")
    return {
        "backend": health.get("search_backend"),
        "index_exists": health.get("index_exists"),
        "doc_count": health.get("doc_count", 0),
        "reranker_available": health.get("reranker_available", False),
    }


def validate_pipeline(**context):
    """Validation minimale des etapes cle."""
    ti = context["ti"]
    scraped_count = ti.xcom_pull(task_ids="scrape_jobs_to_kafka")
    ingestion = ti.xcom_pull(task_ids="wait_for_spark_ingestion")
    cleaning = ti.xcom_pull(task_ids="run_cleaning_from_bronze")
    reindex_decision = ti.xcom_pull(
        task_ids="decide_search_reindex_needed",
        key="search_reindex_decision",
    )
    search_validation = ti.xcom_pull(task_ids="validate_search_index")
    reindex_result = ti.xcom_pull(task_ids="refresh_search_embeddings_index") or {}

    return {
        "scraped_count": scraped_count or 0,
        "scrape_execution": ti.xcom_pull(task_ids="scrape_jobs_to_kafka", key="scrape_execution") or {},
        "bronze_delta": (ingestion or {}).get("delta", 0),
        "bronze_ingested_count": (ingestion or {}).get("delta", 0),
        "cleaned_count": (cleaning or {}).get("cleaned_count", 0),
        "silver_delta_count": (cleaning or {}).get("silver_delta_count", 0),
        "cleaning_errors": (cleaning or {}).get("errors", 0),
        "index_delta_count": ((reindex_result or {}).get("stats") or {}).get("indexed", 0),
        "search_reindex_decision": reindex_decision or {},
        "search_backend": (search_validation or {}).get("backend"),
        "search_docs": (search_validation or {}).get("doc_count", 0),
    }


with DAG(
    dag_id="talentflow_pipeline",
    default_args=default_args,
    description="Pipeline Big Data: Kafka -> Spark Streaming -> MinIO -> Cleaning",
    schedule_interval="0 0,2,4,13,18,20,22 * * *",  # mini run midi + fenetre longue nuit
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=["production", "kafka", "spark", "minio", "airflow"],
) as dag:

    task_snapshot = PythonOperator(
        task_id="snapshot_bronze_before",
        python_callable=snapshot_bronze_before,
    )

    task_scrape = PythonOperator(
        task_id="scrape_jobs_to_kafka",
        python_callable=scrape_jobs_to_kafka,
    )

    task_wait = PythonOperator(
        task_id="wait_for_spark_ingestion",
        python_callable=wait_for_spark_ingestion,
        execution_timeout=timedelta(minutes=25),
    )

    task_clean = PythonOperator(
        task_id="run_cleaning_from_bronze",
        python_callable=run_cleaning_from_bronze,
    )

    task_search_create = PythonOperator(
        task_id="ensure_search_index_ready",
        python_callable=ensure_search_index_ready,
        execution_timeout=timedelta(minutes=5),
    )

    task_search_reindex = PythonOperator(
        task_id="refresh_search_embeddings_index",
        python_callable=refresh_search_embeddings_index,
        execution_timeout=timedelta(hours=2),
    )

    task_search_decide = ShortCircuitOperator(
        task_id="decide_search_reindex_needed",
        python_callable=decide_search_reindex_needed,
        execution_timeout=timedelta(minutes=5),
    )

    task_search_validate = PythonOperator(
        task_id="validate_search_index",
        python_callable=validate_search_index,
        execution_timeout=timedelta(minutes=5),
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    task_validate = PythonOperator(
        task_id="validate_pipeline",
        python_callable=validate_pipeline,
    )

    task_snapshot >> task_scrape >> task_wait >> task_clean
    task_clean >> task_search_create
    task_search_create >> task_search_decide >> task_search_reindex
    [task_search_create, task_search_reindex] >> task_search_validate >> task_validate
