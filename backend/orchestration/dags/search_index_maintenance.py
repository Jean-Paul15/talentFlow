# DAG Airflow de maintenance du moteur de recherche
# Objectif:
# - surveiller la coherence Mongo (Silver) <-> index de recherche
# - reindexer automatiquement seulement si necessaire

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.utils.trigger_rule import TriggerRule
import requests


SEARCH_ENGINE_URL = os.getenv("SEARCH_ENGINE_URL", "http://search-engine:8002")
SEARCH_ENGINE_REQUIRED = str(os.getenv("SEARCH_ENGINE_REQUIRED", "false")).strip().lower() in {"1", "true", "yes", "on"}

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


def ensure_search_index_ready(**context):
    try:
        return _request_json("POST", f"{SEARCH_ENGINE_URL}/index/create?force=false", timeout=120)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}


def get_search_sync_status(**context):
    try:
        status = _request_json("GET", f"{SEARCH_ENGINE_URL}/index/sync-status", timeout=30)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        status = {
            "backend_ok": False,
            "needs_reindex": False,
            "reason": f"search_engine_unavailable: {err}",
        }
    context["ti"].xcom_push(key="sync_status", value=status)
    return status


def decide_reindex_from_status(**context):
    ti = context["ti"]
    status = ti.xcom_pull(task_ids="get_search_sync_status", key="sync_status") or {}
    return bool(status.get("needs_reindex", False))


def run_reindex(**context):
    try:
        return _request_json("POST", f"{SEARCH_ENGINE_URL}/index/reindex?force=false", timeout=7200)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}


def validate_search_index(**context):
    try:
        health = _request_json("GET", f"{SEARCH_ENGINE_URL}/health", timeout=30)
    except Exception as err:
        if SEARCH_ENGINE_REQUIRED:
            raise
        return {"skipped": True, "reason": f"search_engine_unavailable: {err}"}
    if health.get("status") not in ("healthy", "degraded"):
        raise RuntimeError(f"Search-engine unhealthy: {health}")
    if not health.get("index_exists"):
        raise RuntimeError(f"Index/collection absent: {health}")
    return {
        "backend": health.get("search_backend"),
        "doc_count": health.get("doc_count", 0),
        "reranker_available": health.get("reranker_available", False),
    }


with DAG(
    dag_id="search_index_maintenance_hourly",
    default_args=default_args,
    description="Surveille la derive Mongo -> index recherche et reindexe si necessaire",
    schedule_interval="25 0,2,4,13,18,20,22 * * *",  # aligne sur mini-midi + nuit longue
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=["search", "index", "embeddings", "maintenance"],
) as dag:
    task_create = PythonOperator(
        task_id="ensure_search_index_ready",
        python_callable=ensure_search_index_ready,
        execution_timeout=timedelta(minutes=5),
    )

    task_status = PythonOperator(
        task_id="get_search_sync_status",
        python_callable=get_search_sync_status,
        execution_timeout=timedelta(minutes=5),
    )

    task_decide = ShortCircuitOperator(
        task_id="decide_reindex_from_status",
        python_callable=decide_reindex_from_status,
        execution_timeout=timedelta(minutes=5),
    )

    task_reindex = PythonOperator(
        task_id="run_reindex",
        python_callable=run_reindex,
        execution_timeout=timedelta(hours=2),
    )

    task_validate = PythonOperator(
        task_id="validate_search_index",
        python_callable=validate_search_index,
        execution_timeout=timedelta(minutes=5),
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    task_create >> task_status >> task_decide >> task_reindex
    [task_create, task_reindex] >> task_validate
