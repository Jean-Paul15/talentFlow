# Service Redis pour le dashboard

from typing import Any, Dict

import streamlit as st
from loguru import logger

from config import REDIS_URL


@st.cache_resource
def get_redis_client():
    """Retourne un client Redis."""
    try:
        import redis as redis_lib
        parts = REDIS_URL.replace("redis://", "").split(":")
        host = parts[0]
        port_db = parts[1] if len(parts) > 1 else "6379/0"
        port = int(port_db.split("/")[0])
        db = int(port_db.split("/")[1]) if "/" in port_db else 0
        r = redis_lib.Redis(host=host, port=port, db=db, decode_responses=True)
        r.ping()
        return r
    except Exception as err:
        logger.error(f"Redis indisponible: {err}")
    return None


def get_redis_stats() -> Dict[str, Any]:
    """Statistiques Redis."""
    r = get_redis_client()
    if not r:
        return {"status": "indisponible", "total_keys": 0}
    try:
        info = r.info()
        return {
            "status": "connecte",
            "used_memory": info.get("used_memory_human", "N/A"),
            "total_keys": r.dbsize(),
            "uptime_s": info.get("uptime_in_seconds", 0),
        }
    except Exception:
        return {"status": "erreur", "total_keys": 0}
