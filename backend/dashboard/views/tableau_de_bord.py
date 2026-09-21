# Page Tableau de bord - vue d'ensemble du systeme

import streamlit as st
import plotly.express as px

from services.elasticsearch import get_es_stats, jobs_par_source, jobs_par_localisation, jobs_recentes
from services.redis_service import get_redis_stats
from services.minio_service import get_minio_stats
from services.sourcing import statut_sourcing
from services.cleaning import statut_nettoyage
from services.orchestration import get_sites_registry
from services.lake_api import get_lake_stats


def page_tableau_de_bord():
    st.header("Tableau de bord")
    st.caption("Vue d'ensemble du systeme TalentFlow")

    # -- Sante des services ---
    st.subheader("Sante des services")
    col1, col2, col3, col4, col5 = st.columns(5)

    es_stats = get_es_stats()
    redis_stats = get_redis_stats()
    minio_stats = get_minio_stats()
    sourcing = statut_sourcing()
    cleaning = statut_nettoyage()

    with col1:
        s = "OK" if es_stats["status"] in ("green", "yellow") else "KO"
        st.metric("Elasticsearch", s, f"{es_stats.get('total_docs', 0)} docs")
    with col2:
        s = "OK" if redis_stats.get("status") == "connecte" else "KO"
        st.metric("Redis", s, f"{redis_stats.get('total_keys', 0)} cles")
    with col3:
        s = "OK" if minio_stats.get("status") == "connecte" else "KO"
        st.metric("MinIO", s, f"{minio_stats.get('objects', 0)} fichiers")
    with col4:
        st.metric("Sourcing", "OK" if sourcing.get("status") == "running" else "KO")
    with col5:
        st.metric("Nettoyage", "OK" if cleaning.get("status") == "running" else "KO")

    st.divider()

    # -- Sources configurees / alimentees ---
    registry = get_sites_registry()
    lake_stats = get_lake_stats()
    configured_sources = registry.get("sites", {})
    per_site = lake_stats.get("per_site", {})

    total_config = len(configured_sources)
    total_with_data = sum(
        1 for source_id in configured_sources.keys()
        if per_site.get(source_id, 0) > 0
    )

    s1, s2 = st.columns(2)
    with s1:
        st.metric("Sources configurees", total_config)
    with s2:
        st.metric("Sources avec donnees", total_with_data)

    st.divider()

    # -- Graphiques ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("Offres par source")
        df = jobs_par_source()
        if not df.empty:
            fig = px.bar(
                df, x="Source", y="Offres", color="Source",
                height=350, color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(showlegend=False, margin=dict(t=10, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnee. Lancez un scraping depuis l'onglet Sourcing.")

    with col_g2:
        st.subheader("Top localisations")
        df = jobs_par_localisation()
        if not df.empty:
            fig = px.barh(
                df, y="Localisation", x="Offres",
                height=350, color_discrete_sequence=["#2196F3"],
            )
            fig.update_layout(margin=dict(t=10, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnee de localisation.")

    st.divider()

    # -- Derniers resultats ---
    st.subheader("Dernieres offres collectees")
    df = jobs_recentes(15)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune offre indexee pour le moment.")
