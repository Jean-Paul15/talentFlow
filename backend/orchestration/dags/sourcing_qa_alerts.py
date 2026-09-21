# DAG Airflow - Alerting QA sur les sources de scraping
# Objectif:
# - surveiller la qualite des donnees recentes (date/apply/description, erreurs)
# - envoyer des alertes Telegram/Email avec anti-spam (cooldown cote job-sourcing)

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
import requests


JOB_SOURCING_URL = os.getenv("JOB_SOURCING_URL", "http://job-sourcing:8000")
JOB_SOURCING_REQUIRED = str(os.getenv("JOB_SOURCING_REQUIRED", "false")).strip().lower() in {"1", "true", "yes", "on"}
QA_ALERTS_LIMIT = int(os.getenv("QA_ALERTS_LIMIT", "300"))

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


def run_sourcing_qa_alerts(**context):
    """
    Declenche le check QA + envoi d'alertes.
    Le cooldown est gere par job-sourcing (etat local).
    """
    url = (
        f"{JOB_SOURCING_URL}/api/scrape/qa-alerts/check"
        f"?notify=true&force=false&limit={QA_ALERTS_LIMIT}"
    )
    try:
        result = _request_json("POST", url, timeout=120)
    except Exception as err:
        if JOB_SOURCING_REQUIRED:
            raise
        return {"skipped": True, "reason": f"job_sourcing_unavailable: {err}"}

    return {
        "candidate_count": result.get("candidate_count", 0),
        "ready_to_send_count": result.get("ready_to_send_count", 0),
        "suppressed_count": result.get("suppressed_count", 0),
        "delivery": result.get("delivery", {}),
    }


with DAG(
    dag_id="sourcing_qa_alerts_hourly",
    default_args=default_args,
    description="Surveille la QA des spiders et envoie des alertes (Telegram/Email)",
    schedule_interval="35 0,2,4,13,18,20,22 * * *",  # aligne sur mini-midi + nuit longue
    start_date=datetime(2026, 2, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sourcing", "qa", "alerts"],
) as dag:
    task_alerts = PythonOperator(
        task_id="run_sourcing_qa_alerts",
        python_callable=run_sourcing_qa_alerts,
        execution_timeout=timedelta(minutes=5),
    )
