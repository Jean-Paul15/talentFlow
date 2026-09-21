# DAG Airflow - Rebuild complet hebdomadaire de l'index de recherche
# Objectif:
# - nettoyer les documents stale (suppressions cote Mongo non propagees en delta)
# - recreer proprement index ES / collection Qdrant puis reindexer full

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
import requests


SEARCH_ENGINE_URL = os.getenv("SEARCH_ENGINE_URL", "http://search-engine:8002")
SEARCH_ENGINE_REQUIRED = str(os.getenv("SEARCH_ENGINE_REQUIRED", "false")).strip().lower() in {"1", "true", "yes", "on"}

default_args = {
    "owner": "talentflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def _request_json(method: str, url: str, timeout: int = 30, payload=None):
    resp = requests.request(method, url, json=payload, timeout=timeout)
    if resp.status_code >= 300:
        raise RuntimeError(f"HTTP {resp.status_code} on {url}: {resp.text}")
    return resp.json()


def run_full_rebuild(**context):
    """
    Reindex complet (force=true) depuis Mongo vers le backend actif.
    /index/reindex?force=false met a jour l'index/collection sans purge destructive.
    """
    try:
        result = _request_json(
            "POST",
            f"{SEARCH_ENGINE_URL}/index/reindex?force=false",
            timeout=6 * 3600,
        )
        return result
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}


def validate_rebuild(**context):
    try:
        health = _request_json("GET", f"{SEARCH_ENGINE_URL}/health", timeout=30)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}

    if health.get("status") not in ("healthy", "degraded"):
        raise RuntimeError(f"Search-engine unhealthy apres rebuild: {health}")
    if not health.get("index_exists"):
        raise RuntimeError(f"Index/collection absent apres rebuild: {health}")
    return {
        "backend": health.get("search_backend"),
        "doc_count": health.get("doc_count", 0),
        "reranker_available": health.get("reranker_available", False),
    }


with DAG(
    dag_id="search_index_full_rebuild_weekly",
    default_args=default_args,
    description="Rebuild complet hebdomadaire de l'index/collection de recherche",
    schedule_interval=None,  # Desactive en automatique (run manuel uniquement)
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=["search", "index", "maintenance", "weekly"],
) as dag:
    task_rebuild = PythonOperator(
        task_id="run_full_rebuild",
        python_callable=run_full_rebuild,
        execution_timeout=timedelta(hours=6),
    )

    task_validate = PythonOperator(
        task_id="validate_rebuild",
        python_callable=validate_rebuild,
        execution_timeout=timedelta(minutes=5),
    )

    task_rebuild >> task_validate

