# Dashboard executif - mode sourcing_only

import pandas as pd
import plotly.express as px
import streamlit as st

from constants import get_spiders_disponibles
from services.sourcing import lancer_scraping, statut_sourcing
from services.orchestration import get_sourcing_stats
from services.lake_api import get_lake_stats, list_lake_jobs, lake_health


def page_executive_dashboard():
    st.header("Tableau de bord")
    st.caption("Vue globale: collecte, ingestion, stockage et disponibilite des donnees.")

    sourcing_status = statut_sourcing()
    sourcing_stats = get_sourcing_stats()
    lake_stats = get_lake_stats()
    lake_status = lake_health()
    sources = get_spiders_disponibles()
    sources_dediees = {
        source_id: info
        for source_id, info in sources.items()
        if info.get("has_dedicated_folder", False) and info.get("active", True)
    }
    per_site = lake_stats.get("per_site", {})

    total_sources = len(sources_dediees)
    sources_with_data = sum(
        1
        for source_id in sources_dediees
        if per_site.get(source_id, 0) > 0
    )
    total_objects = lake_stats.get("total_objects", 0)
    kafka_ok = sourcing_stats.get("kafka", {}).get("enabled", False)
    minio_ok = bool(sourcing_stats.get("minio", {}).get("bucket"))
    api_ok = lake_status.get("status") == "healthy"
    sourcing_ok = sourcing_status.get("status") in ("running", "healthy", "degraded")
    overall_ok = sourcing_ok and kafka_ok and minio_ok and api_ok

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sources configurees", total_sources)
    with col2:
        st.metric("Sources avec donnees", sources_with_data)
    with col3:
        st.metric("Objets stockes (Bronze)", total_objects)
    with col4:
        st.metric("Pipeline", "Operationnel" if overall_ok else "Partiel")

    st.divider()
    col_action1, col_action2 = st.columns([2, 1])
    with col_action1:
        if st.button("Lancer la collecte maintenant", type="primary", use_container_width=True):
            sites = list(sources_dediees.keys())
            result = lancer_scraping(sites, full=False)
            if result.get("status") in ("success", "scheduled"):
                st.success(
                    f"Collecte lancee. Offres recues: {result.get('count', 0)} "
                    f"| erreurs: {result.get('errors', 0)}"
                )
            else:
                st.error(f"Echec de lancement: {result.get('detail', 'inconnu')}")
    with col_action2:
        if st.button("Actualiser", use_container_width=True):
            st.rerun()

    st.divider()
    st.subheader("Etat des composants")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Sourcing API", "OK" if sourcing_ok else "KO")
    with c2:
        st.metric("Kafka", "OK" if kafka_ok else "KO")
        st.caption(sourcing_stats.get("kafka", {}).get("topic", "topic inconnu"))
    with c3:
        st.metric("MinIO Bronze", "OK" if minio_ok else "KO")
        st.caption(sourcing_stats.get("minio", {}).get("bucket", "-"))
    with c4:
        st.metric("Lake API", "OK" if api_ok else "KO")

    st.divider()
    st.subheader("Repartition des donnees par source")
    if per_site:
        df_sites = pd.DataFrame(
            [{"Source": source, "Objets": count} for source, count in per_site.items()]
        ).sort_values("Objets", ascending=False)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_bar = px.bar(
                df_sites,
                x="Source",
                y="Objets",
                color="Source",
                height=360,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=60))
            st.plotly_chart(fig_bar, use_container_width=True)
        with col_g2:
            fig_pie = px.pie(
                df_sites,
                names="Source",
                values="Objets",
                hole=0.45,
                height=360,
            )
            fig_pie.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Pas encore de donnees stockees. Lancez une collecte.")

    st.divider()
    st.subheader("Sources configurees (dossiers dedies)")
    if sources_dediees:
        source_rows = []
        for source_id, info in sources_dediees.items():
            objects = per_site.get(source_id, 0)
            source_rows.append(
                {
                    "Source ID": source_id,
                    "Label": info.get("label", source_id),
                    "Type": info.get("source_type", "scraping"),
                    "Pays": info.get("pays", "-"),
                    "Provider API": info.get("api_provider") or "-",
                    "Objets Bronze": objects,
                    "Statut data": "Alimentee" if objects > 0 else "Aucune donnee",
                }
            )

        df_sources = pd.DataFrame(source_rows).sort_values(
            ["Objets Bronze", "Source ID"],
            ascending=[False, True],
        )
        st.dataframe(df_sources, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune source dediee detectee.")

    st.divider()
    st.subheader("Dernieres offres recuperees")
    latest = list_lake_jobs(limit=20)
    if latest:
        rows = []
        for obj in latest:
            data = obj.get("data", {})
            rows.append(
                {
                    "Titre": data.get("title", ""),
                    "Entreprise": data.get("company", ""),
                    "Lieu": data.get("location", ""),
                    "Source": data.get("source_site", data.get("source_name", "")),
                    "Date collecte": str(data.get("scraped_at", ""))[:19],
                }
            )
        df_latest = pd.DataFrame(rows)
        st.dataframe(df_latest, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune offre disponible pour le moment.")
