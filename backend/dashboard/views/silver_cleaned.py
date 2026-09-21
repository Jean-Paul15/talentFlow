# Page Silver MongoDB - visualisation des offres nettoyées

import pandas as pd
import streamlit as st

from services.cleaning import list_cleaned_jobs, statut_nettoyage


def page_silver_cleaned():
    st.header("Données nettoyées (MongoDB Silver)")
    st.caption("Visualisation des offres après nettoyage/enrichissement (source: data-cleaning -> MongoDB).")

    status = statut_nettoyage()
    if status.get("status") != "running":
        st.warning("Service data-cleaning indisponible ou non prêt.")
    else:
        st.success(
            f"Service actif | Jobs en MongoDB: {status.get('jobs_in_mongodb', 0)} | Bronze en attente: {status.get('bronze_pending_objects', 0)}"
        )

    st.divider()
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        source = st.text_input("Filtre source (ex: emploi_tg)", value="")
    with col2:
        query = st.text_input("Recherche texte (titre/entreprise/description)", value="")
    with col3:
        country = st.text_input("Filtre pays", value="")
    with col4:
        limit = st.slider("Limite", min_value=10, max_value=200, value=50, step=10)

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        stale_only = st.checkbox("Stale uniquement", value=False)
    with f2:
        expired_only = st.checkbox("Expirées uniquement", value=False)
    with f3:
        min_quality = st.slider("Qualité minimale", min_value=0.0, max_value=1.0, value=0.0, step=0.05)

    data = list_cleaned_jobs(
        limit=limit,
        skip=0,
        source=source.strip() or None,
        query=query.strip() or None,
        country=country.strip() or None,
        stale=True if stale_only else None,
        expired=True if expired_only else None,
        min_quality=min_quality if min_quality > 0 else None,
    )

    if data.get("status") != "success":
        st.error(f"Lecture MongoDB impossible: {data.get('detail', 'erreur inconnue')}")
        return

    total = int(data.get("total", 0))
    items = data.get("items", []) or []
    c1, c2, c3 = st.columns(3)
    c1.metric("Offres nettoyées trouvées", total)
    c2.metric("Sources", len(data.get("sources", []) or []))
    c3.metric("Pays", len(data.get("countries", []) or []))

    sources = data.get("sources", []) or []
    if sources:
        st.caption("Sources disponibles: " + ", ".join(sources[:15]) + ("..." if len(sources) > 15 else ""))

    if not items:
        st.info("Aucune offre trouvée avec les filtres actuels.")
        return

    rows = []
    for j in items:
        rows.append(
            {
                "Titre": j.get("title", ""),
                "Entreprise": j.get("company", ""),
                "Lieu": j.get("location", ""),
                "Pays": j.get("country", ""),
                "Source": j.get("source_name", ""),
                "Qualité": round(float(j.get("quality_score") or 0.0), 3),
                "Stale": bool(j.get("is_stale", False)),
                "Expirée": bool(j.get("is_expired", False)),
                "Fraîcheur (j)": j.get("freshness_days"),
                "Date scrape": str(j.get("scraped_at", ""))[:19],
                "Date traitement": str(j.get("processed_at", ""))[:19],
                "URL": j.get("source_url", ""),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Aperçu détaillé")
    labels = [f"{idx+1}. {item.get('title', 'Sans titre')[:90]}" for idx, item in enumerate(items)]
    selected = st.selectbox("Choisir une offre", options=range(len(items)), format_func=lambda i: labels[i])
    job = items[selected]

    st.markdown(f"### {job.get('title', 'Sans titre')}")
    st.markdown(
        f"**Entreprise:** {job.get('company', '-')} | "
        f"**Lieu:** {job.get('location', '-')}"
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Contrat", job.get("contract_type", "-") or "-")
    with col_b:
        st.metric("Source", job.get("source_name", "-") or "-")
    with col_c:
        st.metric("Pays", job.get("country", "-") or "-")

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Qualité", f"{float(job.get('quality_score') or 0.0):.2f}")
    q2.metric("Fraîcheur (j)", job.get("freshness_days") if job.get("freshness_days") is not None else "-")
    q3.metric("Stale", "Oui" if job.get("is_stale") else "Non")
    q4.metric("Expirée", "Oui" if job.get("is_expired") else "Non")

    st.caption(
        f"Source fraîcheur: {job.get('freshness_source', '-')} | "
        f"TTL: {job.get('freshness_ttl_days', '-')} jours | "
        f"Cause stale: {job.get('stale_reason', '-')}"
    )

    with st.expander("Confiance par champ", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Titre", f"{float(job.get('title_confidence') or 0.0):.2f}")
        c2.metric("Lieu", f"{float(job.get('location_confidence') or 0.0):.2f}")
        c3.metric("Date", f"{float(job.get('date_confidence') or 0.0):.2f}")
        c4.metric("Apply", f"{float(job.get('apply_confidence') or 0.0):.2f}")
        c5.metric("Description", f"{float(job.get('description_confidence') or 0.0):.2f}")

    if job.get("description"):
        with st.expander("Description nettoyée", expanded=False):
            st.write(str(job.get("description"))[:4000])

    skills = job.get("skills", [])
    if skills and isinstance(skills, list):
        st.markdown("**Compétences:** " + ", ".join([str(s) for s in skills[:40]]))

    source_url = job.get("source_url")
    if source_url:
        st.markdown(f"[Voir l'offre originale]({source_url})")

    with st.expander("JSON complet", expanded=False):
        st.json(job)
