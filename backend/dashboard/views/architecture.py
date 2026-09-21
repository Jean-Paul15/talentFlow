# Page Architecture - mode sourcing_only

import streamlit as st

from services.sourcing import statut_sourcing
from services.orchestration import get_sourcing_stats
from services.lake_api import lake_health, get_lake_stats
from config import DASHBOARD_MODE


def page_architecture():
    if DASHBOARD_MODE == "lake_only":
        _page_architecture_lake_only()
        return

    st.header("Architecture Sourcing -> Stockage")
    st.caption("Vue cible: collecte, ingestion event-driven, stockage Bronze, interrogation API.")

    st.code(
        "[Sites Web + APIs]\n"
        "        |\n"
        "        v\n"
        "  Job Sourcing (FastAPI + Scrapy)\n"
        "        |\n"
        "        v\n"
        "      Kafka topic: talentflow_jobs_raw\n"
        "        |\n"
        "        v\n"
        "  Spark Structured Streaming (consumer)\n"
        "        |\n"
        "        v\n"
        "  MinIO Bronze (JSON objets)\n"
        "        |\n"
        "        v\n"
        "     Lake API (FastAPI)\n"
        "        |\n"
        "        v\n"
        "     Streamlit (visualisation)",
        language=None,
    )

    st.divider()
    st.subheader("Etat en temps reel")

    sourcing = statut_sourcing()
    sourcing_stats = get_sourcing_stats()
    lake = lake_health()
    lake_stats = get_lake_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Job Sourcing API",
            "OK" if sourcing.get("status") in ("running", "healthy", "degraded") else "KO",
        )
        st.caption(f"Mode: {sourcing.get('ingestion', 'kafka')}")

    with col2:
        kafka_enabled = sourcing_stats.get("kafka", {}).get("enabled")
        topic = sourcing_stats.get("kafka", {}).get("topic", "talentflow_jobs_raw")
        st.metric("Kafka", "OK" if kafka_enabled else "KO")
        st.caption(f"Topic: {topic}")

    with col3:
        bronze = sourcing_stats.get("minio", {}).get("bronze_objects", 0)
        st.metric("Bronze Objects", bronze)
        st.caption(f"Bucket: {sourcing_stats.get('minio', {}).get('bucket', '-')}")

    with col4:
        st.metric("Lake API", "OK" if lake.get("status") == "healthy" else "KO")
        st.caption(f"Total via API: {lake_stats.get('total_objects', 0)}")

    st.divider()
    st.subheader("Endpoints utilises")
    st.code(
        "GET  /api/status            (job-sourcing)\n"
        "GET  /api/stats             (job-sourcing)\n"
        "GET  /api/bronze/stats      (lake-api)\n"
        "GET  /api/bronze/jobs       (lake-api)\n"
        "GET  /api/bronze/search     (lake-api)",
        language=None,
    )


def _page_architecture_lake_only():
    st.header("Architecture MinIO -> API -> Dashboard")
    st.caption("Mode minimal de demo: stockage Bronze et consultation via API.")

    st.code(
        "[MinIO local]\n"
        "      |\n"
        "      v\n"
        "Sync one-shot vers MinIO serveur\n"
        "      |\n"
        "      v\n"
        "MinIO serveur (bucket Bronze)\n"
        "      |\n"
        "      v\n"
        "Lake API (FastAPI)\n"
        "      |\n"
        "      v\n"
        "Streamlit",
        language=None,
    )

    st.divider()
    lake = lake_health()
    lake_stats = get_lake_stats()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Lake API", "OK" if lake.get("status") == "healthy" else "KO")
    with col2:
        st.metric("Objets Bronze", lake_stats.get("total_objects", 0))

    st.divider()
    st.subheader("Endpoints utilises")
    st.code(
        "GET  /health                (lake-api)\n"
        "GET  /api/bronze/stats      (lake-api)\n"
        "GET  /api/bronze/jobs       (lake-api)\n"
        "GET  /api/bronze/search     (lake-api)",
        language=None,
    )
