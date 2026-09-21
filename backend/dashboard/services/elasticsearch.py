# Service Elasticsearch pour le dashboard
# Client, stats et requetes d'aggregation

from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from loguru import logger

from config import ES_HOST, ES_PORT, ES_INDEX


@st.cache_resource
def get_es_client():
    """Retourne un client Elasticsearch."""
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch([f"http://{ES_HOST}:{ES_PORT}"])
        if es.ping():
            return es
    except Exception as err:
        logger.error(f"Elasticsearch indisponible: {err}")
    return None


def get_es_stats() -> Dict[str, Any]:
    """Statistiques du cluster Elasticsearch."""
    es = get_es_client()
    if not es:
        return {"status": "indisponible", "total_docs": 0, "indices": 0, "size_bytes": 0}
    try:
        health = es.cluster.health()
        stats = es.indices.stats()
        return {
            "status": health["status"],
            "nodes": health["number_of_nodes"],
            "indices": len(stats["indices"]),
            "total_docs": stats["_all"]["primaries"]["docs"]["count"],
            "size_bytes": stats["_all"]["primaries"]["store"]["size_in_bytes"],
        }
    except Exception:
        return {"status": "erreur", "total_docs": 0, "indices": 0, "size_bytes": 0}


def _agg_query(agg_name: str, field: str, size: int = 50) -> pd.DataFrame:
    """Requete d'aggregation generique."""
    es = get_es_client()
    if not es:
        return pd.DataFrame()
    try:
        result = es.search(
            index=ES_INDEX,
            body={"size": 0, "aggs": {agg_name: {"terms": {"field": field, "size": size}}}},
        )
        buckets = result["aggregations"][agg_name]["buckets"]
        return pd.DataFrame({
            "label": [b["key"] for b in buckets],
            "count": [b["doc_count"] for b in buckets],
        })
    except Exception:
        return pd.DataFrame()


def jobs_par_source() -> pd.DataFrame:
    df = _agg_query("sources", "source_name.keyword")
    if not df.empty:
        df.columns = ["Source", "Offres"]
    return df


def jobs_par_localisation() -> pd.DataFrame:
    df = _agg_query("locs", "location.keyword", 15)
    if not df.empty:
        df.columns = ["Localisation", "Offres"]
    return df


def jobs_par_contrat() -> pd.DataFrame:
    df = _agg_query("contrats", "contract_type.keyword", 20)
    if not df.empty:
        df.columns = ["Contrat", "Nombre"]
    return df


def jobs_par_jour() -> pd.DataFrame:
    es = get_es_client()
    if not es:
        return pd.DataFrame()
    try:
        result = es.search(
            index=ES_INDEX,
            body={
                "size": 0,
                "aggs": {
                    "par_jour": {
                        "date_histogram": {
                            "field": "scraped_at",
                            "fixed_interval": "1d",
                            "min_doc_count": 1,
                        }
                    }
                },
            },
        )
        buckets = result["aggregations"]["par_jour"]["buckets"]
        return pd.DataFrame({
            "Date": [b["key_as_string"][:10] for b in buckets],
            "Offres": [b["doc_count"] for b in buckets],
        })
    except Exception:
        return pd.DataFrame()


def jobs_recentes(limit: int = 20) -> pd.DataFrame:
    es = get_es_client()
    if not es:
        return pd.DataFrame()
    try:
        result = es.search(
            index=ES_INDEX,
            body={
                "size": limit,
                "sort": [{"scraped_at": {"order": "desc"}}],
                "_source": ["title", "company", "location", "source_name", "contract_type", "scraped_at"],
            },
        )
        data = []
        for hit in result["hits"]["hits"]:
            s = hit["_source"]
            data.append({
                "Titre": s.get("title", ""),
                "Entreprise": s.get("company", ""),
                "Localisation": s.get("location", ""),
                "Source": s.get("source_name", ""),
                "Contrat": s.get("contract_type", ""),
                "Date": s.get("scraped_at", "")[:10] if s.get("scraped_at") else "",
            })
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def rechercher_offres(query: str, limit: int = 50) -> List[Dict]:
    es = get_es_client()
    if not es:
        return []
    try:
        result = es.search(
            index=ES_INDEX,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "description", "company^2", "location"],
                    }
                },
                "size": limit,
            },
        )
        return [{**hit["_source"], "_score": hit.get("_score", 0)} for hit in result["hits"]["hits"]]
    except Exception:
        return []
