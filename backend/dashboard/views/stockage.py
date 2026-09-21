# Page Stockage - exploration des buckets MinIO avec visualisation JSON

import json

import pandas as pd
import streamlit as st

from services.minio_service import get_minio_client
from services.lake_api import get_lake_stats, list_lake_jobs, search_lake_jobs
from config import DASHBOARD_MODE
from utils import format_bytes


def page_stockage():
    if DASHBOARD_MODE in ("sourcing_only", "lake_only"):
        _page_stockage_api()
        return

    st.header("Stockage MinIO")
    st.caption("Donnees brutes et nettoyees stockees dans MinIO - cliquez sur un objet pour voir son contenu")

    client = get_minio_client()
    if not client:
        st.error("Impossible de se connecter a MinIO.")
        return

    try:
        buckets = client.list_buckets()
    except Exception as err:
        st.error(f"Erreur: {err}")
        return

    if not buckets:
        st.info("Aucun bucket disponible.")
        return

    st.subheader("Buckets")

    for bucket in buckets:
        date_str = bucket.creation_date.strftime("%d/%m/%Y")
        with st.expander(f"{bucket.name} (cree le {date_str})"):
            _afficher_contenu_bucket(client, bucket.name)


def _page_stockage_api():
    st.header("Stockage Bronze via API")
    st.caption("Lecture des donnees Bronze en passant par Lake API (sans acces direct MinIO).")

    stats = get_lake_stats()
    st.metric("Total objets Bronze", stats.get("total_objects", 0))
    st.caption(f"Bucket: {stats.get('bucket', '-')}")

    with st.expander("Repartition par source", expanded=False):
        per_site = stats.get("per_site", {})
        if per_site:
            df = pd.DataFrame(
                [{"Source": site, "Objets": count} for site, count in per_site.items()]
            ).sort_values("Objets", ascending=False)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("Aucune source disponible.")

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        site = st.text_input("Filtre source (site)", value="")
    with col2:
        date_prefix = st.text_input("Filtre date (YYYY-MM-DD)", value="")
    with col3:
        limit = st.slider("Limite", min_value=10, max_value=200, value=50, step=10)

    query = st.text_input("Recherche texte (title, description, company)", value="")

    if query.strip():
        rows = search_lake_jobs(
            query=query.strip(),
            site=site.strip() or None,
            limit=limit,
        )
    else:
        rows = list_lake_jobs(
            site=site.strip() or None,
            date_prefix=date_prefix.strip() or None,
            limit=limit,
        )

    if not rows:
        st.info("Aucun objet trouve.")
        return

    st.subheader(f"Objets retournes: {len(rows)}")
    for row in rows:
        object_name = row.get("object_name", "-")
        payload = row.get("data", {})
        with st.expander(object_name, expanded=False):
            _afficher_offre_formatee(payload)


def _afficher_contenu_bucket(client, bucket_name: str):
    """Affiche le contenu d'un bucket avec exploration interactive."""
    try:
        objects = list(client.list_objects(bucket_name, recursive=True))
        total = len(objects)
        st.write(f"**{total} objet(s)**")

        if not objects:
            return

        # Regrouper par spider/dossier
        folders = {}
        for obj in objects:
            parts = obj.object_name.split('/')
            folder = parts[0] if len(parts) > 1 else "(racine)"
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(obj)

        # Afficher par dossier avec compteur
        for folder, folder_objects in sorted(folders.items()):
            with st.expander(f"{folder} ({len(folder_objects)} fichier(s))"):
                _afficher_dossier(client, bucket_name, folder_objects)

    except Exception as err:
        st.error(f"Erreur lecture: {err}")


def _afficher_dossier(client, bucket_name: str, objects: list):
    """Affiche les fichiers d'un dossier avec visualisation au clic."""
    # Limiter l'affichage
    display_objects = objects[:50]

    for obj in display_objects:
        name = obj.object_name
        short_name = name.rsplit('/', 1)[-1] if '/' in name else name
        size = format_bytes(obj.size) if obj.size else "0 o"
        date = obj.last_modified.strftime("%d/%m %H:%M") if obj.last_modified else ""

        # Bouton pour afficher le contenu JSON
        col1, col2, col3 = st.columns([5, 2, 2])
        with col1:
            btn_key = f"view_{bucket_name}_{name}"
            if st.button(f"{short_name}", key=btn_key, use_container_width=True):
                _afficher_contenu_objet(client, bucket_name, name)
        with col2:
            st.caption(size)
        with col3:
            st.caption(date)

    if len(objects) > 50:
        st.caption(f"Affichage limite aux 50 premiers sur {len(objects)}.")


def _afficher_contenu_objet(client, bucket_name: str, object_name: str):
    """Telecharge et affiche le contenu d'un objet MinIO."""
    try:
        response = client.get_object(bucket_name, object_name)
        raw_data = response.read()
        response.close()
        response.release_conn()

        # Tenter le parsing JSON
        try:
            content = json.loads(raw_data.decode("utf-8"))
            st.divider()
            st.subheader(f"Contenu : {object_name.rsplit('/', 1)[-1]}")

            # Affichage structure de l'offre
            if isinstance(content, dict):
                _afficher_offre_formatee(content)
            else:
                st.json(content)

        except (json.JSONDecodeError, UnicodeDecodeError):
            st.info(f"Fichier binaire ({len(raw_data)} octets) - apercu non disponible")

    except Exception as err:
        st.error(f"Erreur lecture objet: {err}")


def _afficher_offre_formatee(job: dict):
    """Affiche une offre d'emploi de facon lisible et structuree."""
    # En-tete
    title = job.get("title", "Sans titre")
    company = job.get("company", "Non precise")
    location = job.get("location", "Non precise")
    st.markdown(f"### {title}")
    st.markdown(f"**Entreprise :** {company} | **Lieu :** {location}")

    # Recruteur (si different de l'entreprise)
    recruiter = job.get("recruiter_name")
    if recruiter and recruiter.lower() != company.lower():
        st.markdown(f"**Recruteur / Cabinet :** {recruiter}")

    # Ligne 1 : contrat, source, date scraping
    col1, col2, col3 = st.columns(3)
    with col1:
        contract = job.get("contract_type", "-")
        st.metric("Contrat", contract if contract else "-")
    with col2:
        source = job.get("source_name", "-")
        st.metric("Source", source if source else "-")
    with col3:
        scraped = job.get("scraped_at", "-")
        if scraped and len(scraped) > 10:
            scraped = scraped[:10]
        st.metric("Date scraping", scraped if scraped else "-")

    # Ligne 2 : pays, secteur, salaire
    country = job.get("country")
    sector = job.get("sector")
    salary = job.get("salary")
    if country or sector or salary:
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("Pays", country if country else "-")
        with col5:
            st.metric("Secteur", sector if sector else "-")
        with col6:
            st.metric("Salaire", salary if salary else "-")

    # Ligne 3 : experience, education, deadline
    experience = job.get("experience")
    education = job.get("education")
    deadline = job.get("deadline")
    if experience or education or deadline:
        col7, col8, col9 = st.columns(3)
        with col7:
            st.metric("Experience", experience if experience else "-")
        with col8:
            st.metric("Diplome", education if education else "-")
        with col9:
            st.metric("Date limite", deadline if deadline else "-")

    # Contact (email, telephone)
    email = job.get("contact_email")
    phone = job.get("contact_phone")
    if email or phone:
        contact_parts = []
        if email:
            contact_parts.append(f"Email : {email}")
        if phone:
            contact_parts.append(f"Tel : {phone}")
        st.info(" | ".join(contact_parts))

    # Bouton Postuler
    apply_url = job.get("apply_url")
    if apply_url:
        st.markdown(
            f'<a href="{apply_url}" target="_blank" '
            f'style="background-color:#4CAF50;color:white;padding:8px 20px;'
            f'text-decoration:none;border-radius:5px;font-weight:bold;">'
            f'Postuler ici</a>',
            unsafe_allow_html=True,
        )

    # Description
    desc = job.get("description", "")
    if desc:
        with st.expander("Description complete", expanded=False):
            st.write(desc[:3000])

    # Competences
    skills = job.get("skills", [])
    if skills:
        st.markdown(f"**Competences :** {', '.join(skills)}")

    # Date publication
    posted = job.get("posted_date")
    if posted:
        st.caption(f"Publie le : {posted}")

    # Donnees supplementaires capturees (catch-all)
    extra = job.get("extra_data", {})
    if extra and isinstance(extra, dict):
        # Champs enrichis importants affiches en priorite
        _afficher_extras_prioritaires(extra)

        # Tous les autres champs inconnus
        reste = {
            k: v for k, v in extra.items()
            if not k.startswith("_") and k not in _EXTRAS_PRIORITAIRES
        }
        if reste:
            with st.expander(
                f"Autres informations ({len(reste)} champs)", expanded=False
            ):
                for label, value in reste.items():
                    display_label = label.replace("_", " ").capitalize()
                    if isinstance(value, (list, dict)):
                        st.markdown(f"**{display_label} :**")
                        st.json(value)
                    else:
                        st.markdown(f"**{display_label} :** {value}")

        # Donnees brutes JSON-LD archivees
        raw_jsonld = extra.get("_jsonld_raw")
        if raw_jsonld:
            with st.expander("JSON-LD brut (archive complete)", expanded=False):
                st.json(raw_jsonld)

    # URL source
    url = job.get("source_url", "")
    if url:
        st.markdown(f"[Voir l'offre originale]({url})")

    # JSON brut complet
    with st.expander("JSON brut complet", expanded=False):
        st.json(job)


# Cles prioritaires de extra_data a afficher en premier
_EXTRAS_PRIORITAIRES = {
    "benefits", "work_hours", "responsibilities", "remote_type",
    "total_openings", "langues_requises", "reference_offre",
    "adresse_physique", "nb_postes", "geo_coordinates",
    "company_url", "og_image",
}


def _afficher_extras_prioritaires(extra: dict):
    """Affiche les champs enrichis importants dans des widgets dedies."""
    displayed = False

    benefits = extra.get("benefits")
    work_hours = extra.get("work_hours")
    remote_type = extra.get("remote_type")
    if benefits or work_hours or remote_type:
        displayed = True
        cols = st.columns(3)
        with cols[0]:
            st.metric("Avantages", benefits[:50] if benefits else "-")
        with cols[1]:
            st.metric("Horaires", work_hours[:30] if work_hours else "-")
        with cols[2]:
            st.metric("Teletravail", remote_type[:30] if remote_type else "-")

    langues = extra.get("langues_requises")
    reference = extra.get("reference_offre")
    nb_postes = extra.get("nb_postes") or extra.get("total_openings")
    if langues or reference or nb_postes:
        displayed = True
        cols = st.columns(3)
        with cols[0]:
            st.metric("Langues", langues[:40] if langues else "-")
        with cols[1]:
            st.metric("Reference", reference[:20] if reference else "-")
        with cols[2]:
            st.metric("Nb postes", nb_postes if nb_postes else "-")

    responsibilities = extra.get("responsibilities")
    if responsibilities:
        displayed = True
        with st.expander("Responsabilites", expanded=False):
            st.write(str(responsibilities)[:2000])

    if displayed:
        st.divider()
