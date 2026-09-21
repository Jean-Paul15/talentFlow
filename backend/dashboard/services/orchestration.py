# Service API Airflow / Orchestration pour le dashboard
# Interroge le service job-sourcing pour les horaires et les sites

from typing import Any, Dict, List

import requests
from loguru import logger

from config import JOB_SOURCING_URL, AIRFLOW_URL


def get_schedule() -> Dict[str, Any]:
    """Recupere les horaires d'orchestration depuis le registre de sites."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/schedule", timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as err:
        logger.warning(f"Schedule indisponible: {err}")
    return {"sites": [], "dags": {}}


def get_sites_registry() -> Dict[str, Any]:
    """Recupere la liste complete des sites depuis le registre."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/sites", timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as err:
        logger.warning(f"Registre sites indisponible: {err}")
    return {"total": 0, "sites": {}}


def get_sourcing_stats() -> Dict[str, Any]:
    """Recupere les stats du pipeline de sourcing."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/stats", timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as err:
        logger.warning(f"Stats sourcing indisponibles: {err}")
    return {}


def get_orchestration_settings() -> Dict[str, Any]:
    """Recupere la configuration d'orchestration (crons + activation DAGs)."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/orchestration/settings", timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as err:
        logger.warning(f"Settings orchestration indisponibles: {err}")
    return {"priority_crons": {}, "dag_enabled": {}, "priority_schedule": {}}


def update_orchestration_settings(
    priority_crons: Dict[str, str] = None,
    dag_enabled: Dict[str, bool] = None,
) -> Dict[str, Any]:
    """Met a jour la programmation Airflow via job-sourcing."""
    payload: Dict[str, Any] = {}
    if priority_crons is not None:
        payload["priority_crons"] = priority_crons
    if dag_enabled is not None:
        payload["dag_enabled"] = dag_enabled

    try:
        resp = requests.put(
            f"{JOB_SOURCING_URL}/api/orchestration/settings",
            json=payload,
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def list_airflow_dags() -> Dict[str, Any]:
    """Liste des DAGs Airflow (via proxy job-sourcing)."""
    try:
        resp = requests.get(
            f"{JOB_SOURCING_URL}/api/orchestration/dags",
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}", "dags": []}
    except Exception as err:
        return {"status": "erreur", "detail": str(err), "dags": []}


def set_airflow_dag_pause(dag_id: str, paused: bool) -> Dict[str, Any]:
    """Pause/reprise d'un DAG Airflow."""
    try:
        resp = requests.patch(
            f"{JOB_SOURCING_URL}/api/orchestration/dags/{dag_id}/pause",
            json={"paused": paused},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def trigger_airflow_dag(dag_id: str, conf: Dict[str, Any] = None) -> Dict[str, Any]:
    """Declenchement manuel d'un DAG."""
    try:
        resp = requests.post(
            f"{JOB_SOURCING_URL}/api/orchestration/dags/{dag_id}/trigger",
            json={"conf": conf or {}},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def lancer_purge() -> Dict[str, Any]:
    """Purge complete Redis + MinIO."""
    try:
        resp = requests.post(
            f"{JOB_SOURCING_URL}/api/purge", timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def lancer_purge_et_rescrape(sites: List[str] = None) -> Dict[str, Any]:
    """Purge complete + relance du scraping."""
    try:
        payload = {"sites": sites or [], "full": not sites}
        resp = requests.post(
            f"{JOB_SOURCING_URL}/api/purge-and-rescrape",
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "erreur", "detail": f"Code HTTP {resp.status_code}"}
    except Exception as err:
        return {"status": "erreur", "detail": str(err)}


def statut_airflow() -> Dict[str, Any]:
    """Verifie le statut du serveur Airflow."""
    try:
        resp = requests.get(
            f"{AIRFLOW_URL}/health", timeout=5,
        )
        if resp.status_code == 200:
            return {"status": "operationnel", "data": resp.json()}
    except Exception:
        pass
    return {"status": "indisponible"}
