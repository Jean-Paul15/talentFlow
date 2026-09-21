# Dashboard minimal pour mode lake_only (MinIO + Lake API).

import pandas as pd
import plotly.express as px
import streamlit as st

from config import LAKE_API_URL
from services.lake_api import (
    get_lake_stats,
    lake_health,
    list_lake_jobs,
    list_lake_sources,
    list_lake_source_examples,
)
from services.minio_service import get_minio_stats


def _build_sources_df(sources: list[dict]) -> pd.DataFrame:
    if not sources:
        return pd.DataFrame(columns=["Source", "Objets", "Dernier objet", "Derniere modif", "Exemples titres"])

    rows = []
    for src in sources:
        rows.append(
            {
                "Source": src.get("source", ""),
                "Objets": int(src.get("total_objects", 0) or 0),
                "Dernier objet": src.get("latest_object", ""),
                "Derniere modif": str(src.get("latest_modified", ""))[:19],
                "Exemples titres": " | ".join(src.get("sample_titles", [])),
            }
        )
    return pd.DataFrame(rows).sort_values("Objets", ascending=False)


def page_lake_dashboard():
    st.header("Tableau de bord API Lake")
    st.caption("Mode demo serveur: MinIO Bronze -> Lake API -> visualisation decisionnelle.")

    lake = lake_health()
    lake_stats = get_lake_stats()
    minio_stats = get_minio_stats()
    sources = list_lake_sources(sample_limit=2)
    df_sources = _build_sources_df(sources)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("MinIO", "OK" if minio_stats.get("status") == "connecte" else "KO")
    with col2:
        st.metric("Lake API", "OK" if lake.get("status") == "healthy" else "KO")
    with col3:
        st.metric("Objets Bronze", lake_stats.get("total_objects", 0))
    with col4:
        st.metric("Sources", len(sources))

    st.divider()
    st.subheader("Repartition des donnees")
    if not df_sources.empty:
        chart_col1, chart_col2 = st.columns([2, 1])
        with chart_col1:
            fig_bar = px.bar(
                df_sources.head(12),
                x="Source",
                y="Objets",
                color="Objets",
                color_continuous_scale="Blues",
                title="Volume d'objets par source",
            )
            fig_bar.update_layout(height=360, margin=dict(t=40, l=10, r=10, b=60))
            st.plotly_chart(fig_bar, use_container_width=True)
        with chart_col2:
            fig_pie = px.pie(
                df_sources.head(8),
                names="Source",
                values="Objets",
                hole=0.55,
                title="Top sources",
            )
            fig_pie.update_layout(height=360, margin=dict(t=40, l=10, r=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aucune donnee Bronze detectee. Lance d'abord la commande de synchronisation.")

    st.divider()
    st.subheader("Catalogue des sources (API)")
    if not df_sources.empty:
        st.dataframe(df_sources, use_container_width=True, hide_index=True)

        # Insights directs pour soutenance.
        top_source = df_sources.iloc[0]
        total = max(int(df_sources["Objets"].sum()), 1)
        dominance = round((int(top_source["Objets"]) / total) * 100, 1)
        insight_col1, insight_col2, insight_col3 = st.columns(3)
        insight_col1.metric("Source la plus active", top_source["Source"])
        insight_col2.metric("Objets top source", int(top_source["Objets"]))
        insight_col3.metric("Part du top", f"{dominance}%")

        source_names = [src.get("source", "") for src in sources if src.get("source")]
        selected_source = st.selectbox("Voir des exemples d'une source", source_names)
        examples = list_lake_source_examples(selected_source, limit=20)
        if examples:
            ex_rows = []
            for obj in examples:
                payload = obj.get("data", {})
                ex_rows.append(
                    {
                        "Titre": payload.get("title", ""),
                        "Entreprise": payload.get("company", ""),
                        "Lieu": payload.get("location", ""),
                        "Objet": obj.get("object_name", ""),
                    }
                )
            st.dataframe(pd.DataFrame(ex_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Pas d'exemple pour cette source.")
    else:
        st.info("Endpoint /api/bronze/sources vide pour le moment.")

    st.divider()
    st.subheader("Dernieres offres consolidees")
    jobs = list_lake_jobs(limit=20)
    if not jobs:
        st.info("Aucune offre disponible.")
    else:
        rows = []
        for obj in jobs:
            data = obj.get("data", {})
            rows.append(
                {
                    "Titre": data.get("title", ""),
                    "Entreprise": data.get("company", ""),
                    "Lieu": data.get("location", ""),
                    "Source": data.get("source_site", data.get("source_name", "")),
                    "Objet": obj.get("object_name", ""),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("API Lake detaillee (demo)")
    st.markdown(
        f"- Swagger: `{LAKE_API_URL}/docs`\n"
        f"- Health: `{LAKE_API_URL}/health`\n"
        f"- Sources: `{LAKE_API_URL}/api/bronze/sources`\n"
        f"- Jobs: `{LAKE_API_URL}/api/bronze/jobs`\n"
        f"- Search: `{LAKE_API_URL}/api/bronze/search`"
    )
    st.code(
        f"Base: {LAKE_API_URL}\n"
        f"GET {LAKE_API_URL}/health\n"
        f"GET {LAKE_API_URL}/api/bronze/stats\n"
        f"GET {LAKE_API_URL}/api/bronze/sources?sample_limit=2\n"
        f"GET {LAKE_API_URL}/api/bronze/sources/<site>/examples?limit=20\n"
        f"GET {LAKE_API_URL}/api/bronze/jobs?site=wiijob&limit=20\n"
        f"GET {LAKE_API_URL}/api/bronze/search?q=python&limit=20\n"
        f"GET {LAKE_API_URL}/docs",
        language=None,
    )
