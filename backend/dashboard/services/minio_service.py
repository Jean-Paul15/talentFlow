# Service MinIO pour le dashboard

from typing import Any, Dict

import streamlit as st
from loguru import logger

from config import MINIO_HOST, MINIO_USER, MINIO_PASS


@st.cache_resource
def get_minio_client():
    """Retourne un client MinIO."""
    try:
        from minio import Minio
        client = Minio(
            MINIO_HOST,
            access_key=MINIO_USER,
            secret_key=MINIO_PASS,
            secure=False,
        )
        client.list_buckets()
        return client
    except Exception as err:
        logger.error(f"MinIO indisponible: {err}")
    return None


def get_minio_stats() -> Dict[str, Any]:
    """Statistiques MinIO."""
    client = get_minio_client()
    if not client:
        return {"status": "indisponible", "buckets": 0, "objects": 0, "size": 0}
    try:
        buckets = client.list_buckets()
        total_obj = 0
        total_size = 0
        for b in buckets:
            try:
                for obj in client.list_objects(b.name, recursive=True):
                    total_obj += 1
                    total_size += obj.size or 0
            except Exception:
                pass
        return {
            "status": "connecte",
            "buckets": len(buckets),
            "objects": total_obj,
            "size": total_size,
        }
    except Exception:
        return {"status": "erreur", "buckets": 0, "objects": 0, "size": 0}
