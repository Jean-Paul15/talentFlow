# Page Flux de donnees - visualisation du pipeline

import streamlit as st

from services.sourcing import statut_sourcing
from services.orchestration import get_sourcing_stats
from services.lake_api import get_lake_stats, lake_health
from config import DASHBOARD_MODE


def page_flux():
    st.header("Flux de donnees")
    st.caption("Pipeline collecte -> Kafka -> Spark -> MinIO -> API")

    # -- Schema du pipeline ---
    st.subheader("Architecture du pipeline")
    st.code(
        "  [Sites Web + APIs]\n"
        "          |\n"
        "          v\n"
        "  Job Sourcing (Scrapy + FastAPI)\n"
        "          |\n"
        "          v\n"
        "       Kafka topic (raw events)\n"
        "          |\n"
        "          v\n"
        "  Spark Structured Streaming consumer\n"
        "          |\n"
        "          v\n"
        "   MinIO Bronze (JSON)\n"
        "          |\n"
        "          v\n"
        "      Lake API + Streamlit",
        language=None,
    )

    st.divider()

    # -- Etat des etapes ---
    st.subheader("Etat des etapes")
    col1, col2, col3, col4 = st.columns(4)
    sourcing = statut_sourcing()
    stats = get_sourcing_stats()
    lake = lake_health()
    lake_stats = get_lake_stats()

    with col1:
        st.markdown("**Etape 1 : Sourcing API**")
        if sourcing.get("status") in ("running", "healthy", "degraded"):
            st.success("Operationnel")
            for s in sourcing.get("spiders_available", []):
                st.caption(f"- {s}")
        else:
            st.error("Indisponible")

    with col2:
        st.markdown("**Etape 2 : Kafka ingest**")
        kafka = stats.get("kafka", {})
        if kafka.get("enabled"):
            st.success("Operationnel")
            st.write(f"Topic : `{kafka.get('topic', '-')}`")
        else:
            st.error("Indisponible")

    with col3:
        st.markdown("**Etape 3 : Bronze MinIO**")
        minio = stats.get("minio", {})
        objects = minio.get("bronze_objects", 0)
        if minio.get("bucket"):
            st.success("Operationnel")
            st.write(f"Fichiers : {objects}")
            st.write(f"Bucket : {minio.get('bucket', '-')}")
        else:
            st.error("Indisponible")

    with col4:
        st.markdown("**Etape 4 : Lake API**")
        if lake.get("status") == "healthy":
            st.success("Operationnel")
            st.write(f"Objets vus API : {lake_stats.get('total_objects', 0)}")
        else:
            st.error("Indisponible")

    if DASHBOARD_MODE != "sourcing_only":
        st.info("Mode complet: d'autres etapes aval (cleaning/index/recherche) existent mais ne sont pas affichees ici.")
