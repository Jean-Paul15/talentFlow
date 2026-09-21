# Page Statistiques - graphiques et metriques

import streamlit as st
import plotly.express as px

from services.elasticsearch import (
    get_es_stats,
    jobs_par_source,
    jobs_par_contrat,
    jobs_par_jour,
)
from services.redis_service import get_redis_stats
from services.minio_service import get_minio_stats
from utils import format_bytes


def page_statistiques():
    st.header("Statistiques")
    st.caption("Analyse des donnees collectees")

    # -- Evolution temporelle ---
    st.subheader("Evolution des offres collectees")
    df_time = jobs_par_jour()
    if not df_time.empty:
        fig = px.line(
            df_time, x="Date", y="Offres", markers=True,
            height=300, color_discrete_sequence=["#4CAF50"],
        )
        fig.update_layout(margin=dict(t=10, b=40))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de donnees temporelles.")

    st.divider()

    # -- Repartitions ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Repartition par contrat")
        df_c = jobs_par_contrat()
        if not df_c.empty:
            fig = px.pie(
                df_c, values="Nombre", names="Contrat",
                height=350, color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de donnees de contrats.")

    with col2:
        st.subheader("Repartition par source")
        df_s = jobs_par_source()
        if not df_s.empty:
            fig = px.pie(
                df_s, values="Offres", names="Source",
                height=350, color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de donnees de sources.")

    st.divider()

    # -- Metriques systeme ---
    st.subheader("Metriques systeme")
    col_m1, col_m2, col_m3 = st.columns(3)

    es = get_es_stats()
    redis_s = get_redis_stats()
    minio_s = get_minio_stats()

    with col_m1:
        st.metric("Documents Elasticsearch", f"{es.get('total_docs', 0):,}")
        st.metric("Index", es.get("indices", 0))
        st.metric("Taille", format_bytes(es.get("size_bytes", 0)))

    with col_m2:
        st.metric("Cles Redis", f"{redis_s.get('total_keys', 0):,}")
        st.metric("Memoire utilisee", redis_s.get("used_memory", "N/A"))

    with col_m3:
        st.metric("Fichiers MinIO", f"{minio_s.get('objects', 0):,}")
        st.metric("Buckets", minio_s.get("buckets", 0))
        st.metric("Taille totale", format_bytes(minio_s.get("size", 0)))
