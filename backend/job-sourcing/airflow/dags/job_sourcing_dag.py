# DAG Airflow pour orchestration du scraping
# Strategie : lit le registre de sites dynamiquement via API
# Ajouter un site dans sites_registry.py = Airflow le prend en compte

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
import logging

logger = logging.getLogger(__name__)

JOB_SOURCING_URL = os.getenv("JOB_SOURCING_URL", "http://job-sourcing:8000")

default_args = {
    "owner": "talentflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=1),
}


def _fetch_dag_config():
    """Recupere la config des DAGs depuis le registre de sites."""
    import requests
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/schedule", timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("dags", {})
    except Exception as err:
        logger.warning(f"Registre indisponible, config par defaut: {err}")
    # Fallback si l'API est down au moment du parsing des DAGs
    return None


def _call_scrape(sites: list, full: bool = False):
    """Appelle l'API scrape du service job-sourcing."""
    import requests

    url = f"{JOB_SOURCING_URL}/api/scrape"
    payload = {"sites": sites, "full": full}

    logger.info(f"Appel API scrape: {url} avec {sites}")
    resp = requests.post(url, json=payload, timeout=3600)

    if resp.status_code != 200:
        raise Exception(f"Scrape echoue ({resp.status_code}): {resp.text}")

    data = resp.json()
    logger.info(f"Scrape termine: {data}")
    return data


def _call_stats():
    """Recupere les stats du pipeline."""
    import requests

    url = f"{JOB_SOURCING_URL}/api/stats"
    resp = requests.get(url, timeout=30)
    data = resp.json()
    logger.info(f"Stats pipeline: {data}")
    return data


# -------------------------------------------------------------------
# Configuration dynamique depuis le registre
# Si l'API est down, on utilise une config par defaut
# -------------------------------------------------------------------
_dynamic_config = _fetch_dag_config()

if _dynamic_config:
    # Config depuis le registre de sites
    _p1_spiders = _dynamic_config.get("1", {}).get("spiders", [])
    _p2_spiders = _dynamic_config.get("2", {}).get("spiders", [])
    _p3_spiders = _dynamic_config.get("3", {}).get("spiders", [])
    _p4_spiders = _dynamic_config.get("4", {}).get("spiders", [])

    _p1_cron = _dynamic_config.get("1", {}).get("cron", "0 0,2,4,13,18,20,22 * * *")
    _p2_cron = _dynamic_config.get("2", {}).get("cron", "10 0,2,4,18,22 * * *")
    _p3_cron = _dynamic_config.get("3", {}).get("cron", "40 13 * * *")
    _p4_cron = _dynamic_config.get("4", {}).get("cron", "0 1 * * *")

    _p1_enabled = bool(_dynamic_config.get("1", {}).get("enabled", True))
    _p2_enabled = bool(_dynamic_config.get("2", {}).get("enabled", True))
    _p3_enabled = bool(_dynamic_config.get("3", {}).get("enabled", False))
    _p4_enabled = bool(_dynamic_config.get("4", {}).get("enabled", True))

    _p1_total = _dynamic_config.get("1", {}).get("total_sites", 0)
    _p2_total = _dynamic_config.get("2", {}).get("total_sites", 0)
    _p3_total = _dynamic_config.get("3", {}).get("total_sites", 0)
    _p4_total = _dynamic_config.get("4", {}).get("total_sites", 0)
else:
    # Fallback par defaut
    _p1_spiders = ["emploi_tg", "anpe_togo", "deep_crawler"]
    _p2_spiders = ["miabejob", "emploitogo_com", "deep_crawler"]
    _p3_spiders = ["emploitogo_info", "wiijob", "deep_crawler"]
    _p4_spiders = ["deep_crawler"]

    _p1_cron = "0 0,2,4,13,18,20,22 * * *"
    _p2_cron = "10 0,2,4,18,22 * * *"
    _p3_cron = "40 13 * * *"
    _p4_cron = "0 1 * * *"

    _p1_enabled = True
    _p2_enabled = True
    _p3_enabled = False
    _p4_enabled = True

    _p1_total = 2
    _p2_total = 4
    _p3_total = 7
    _p4_total = 8

logger.info(
    f"DAGs configures: "
    f"P1(cron={_p1_cron}, enabled={_p1_enabled}), "
    f"P2(cron={_p2_cron}, enabled={_p2_enabled}), "
    f"P3(cron={_p3_cron}, enabled={_p3_enabled}), "
    f"P4(cron={_p4_cron}, enabled={_p4_enabled})"
)


def scrape_priority_1(**context):
    """Sites haute priorite (Togo principaux)."""
    return _call_scrape(_p1_spiders)


def scrape_priority_2(**context):
    """Sites priorite moyenne (Togo + Afrique)."""
    return _call_scrape(_p2_spiders)


def scrape_priority_3(**context):
    """Sites basse priorite (portails secondaires)."""
    return _call_scrape(_p3_spiders)


def scrape_full(**context):
    """Scrape complet nocturne : tous les spiders."""
    return _call_scrape(_p4_spiders + _p3_spiders + _p2_spiders + _p1_spiders)


def validate_pipeline(**context):
    """Valide l'integrite du pipeline (Redis + MinIO)."""
    return _call_stats()


# ----------------------------------------------------------------
# DAG 1 : Haute frequence (2x/jour) - sites Togo prioritaires
# ----------------------------------------------------------------
with DAG(
    dag_id="sourcing_priority_1_high_frequency",
    default_args=default_args,
    description=f"Sites P1: {', '.join(_p1_spiders)} ({_p1_total} sites, 2x/jour)",
    schedule_interval=_p1_cron if _p1_enabled else None,
    start_date=datetime(2026, 2, 1),
    catchup=False,
    is_paused_upon_creation=not _p1_enabled,
    max_active_runs=1,
    tags=["sourcing", "togo", "priority_1", "high_frequency"],
) as dag_p1:

    scrape_p1 = PythonOperator(
        task_id="scrape_p1",
        python_callable=scrape_priority_1,
        execution_timeout=timedelta(hours=1),
    )

    validate_p1 = PythonOperator(
        task_id="validate_p1",
        python_callable=validate_pipeline,
        execution_timeout=timedelta(minutes=5),
    )

    scrape_p1 >> validate_p1


# ----------------------------------------------------------------
# DAG 2 : Frequence moyenne (1x/jour)
# ----------------------------------------------------------------
with DAG(
    dag_id="sourcing_priority_2_medium_frequency",
    default_args=default_args,
    description=f"Sites P2: {', '.join(_p2_spiders)} ({_p2_total} sites, 1x/jour)",
    schedule_interval=_p2_cron if _p2_enabled else None,
    start_date=datetime(2026, 2, 1),
    catchup=False,
    is_paused_upon_creation=not _p2_enabled,
    max_active_runs=1,
    tags=["sourcing", "togo", "priority_2", "medium_frequency"],
) as dag_p2:

    scrape_p2 = PythonOperator(
        task_id="scrape_p2",
        python_callable=scrape_priority_2,
        execution_timeout=timedelta(hours=1),
    )

    validate_p2 = PythonOperator(
        task_id="validate_p2",
        python_callable=validate_pipeline,
        execution_timeout=timedelta(minutes=5),
    )

    scrape_p2 >> validate_p2


# ----------------------------------------------------------------
# DAG 3 : Basse frequence (desactivee par defaut) - portails secondaires
# ----------------------------------------------------------------
with DAG(
    dag_id="sourcing_priority_3_low_frequency",
    default_args=default_args,
    description=f"Sites P3: {', '.join(_p3_spiders)} ({_p3_total} sites, 1x/jour)",
    schedule_interval=_p3_cron if _p3_enabled else None,
    start_date=datetime(2026, 2, 1),
    catchup=False,
    is_paused_upon_creation=not _p3_enabled,
    max_active_runs=1,
    tags=["sourcing", "togo", "priority_3", "low_frequency"],
) as dag_p3:

    scrape_p3 = PythonOperator(
        task_id="scrape_p3",
        python_callable=scrape_priority_3,
        execution_timeout=timedelta(hours=1),
    )

    validate_p3 = PythonOperator(
        task_id="validate_p3",
        python_callable=validate_pipeline,
        execution_timeout=timedelta(minutes=5),
    )

    scrape_p3 >> validate_p3


# ----------------------------------------------------------------
# DAG 4 : Full crawl nocturne - tous les sites
# ----------------------------------------------------------------
with DAG(
    dag_id="sourcing_full_crawl_nightly",
    default_args=default_args,
    description=f"Full crawl nocturne ({_p4_total + _p3_total + _p2_total + _p1_total} sites)",
    schedule_interval=_p4_cron if _p4_enabled else None,
    start_date=datetime(2026, 2, 1),
    catchup=False,
    is_paused_upon_creation=not _p4_enabled,
    max_active_runs=1,
    tags=["sourcing", "full", "nightly"],
) as dag_full:

    full_scrape = PythonOperator(
        task_id="full_scrape",
        python_callable=scrape_full,
        execution_timeout=timedelta(hours=3),
    )

    validate_full = PythonOperator(
        task_id="validate_full",
        python_callable=validate_pipeline,
        execution_timeout=timedelta(minutes=5),
    )

    full_scrape >> validate_full
