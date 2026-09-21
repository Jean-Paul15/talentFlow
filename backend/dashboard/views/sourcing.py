# Page Sourcing - selection de spiders et lancement manuel
# Les sites sont charges dynamiquement depuis le registre API

import streamlit as st

from constants import get_spiders_disponibles
from services.sourcing import lancer_scraping, statut_sourcing
from services.cleaning import lancer_nettoyage
from config import DASHBOARD_MODE


def page_sourcing():
    st.header("Sourcing des offres")
    st.caption("Selectionnez les sources (scraping + APIs) et lancez la collecte")

    # -- Statut du service ---
    status = statut_sourcing()
    if status.get("status") == "running":
        st.success("Service de sourcing operationnel")
    else:
        st.warning("Service de sourcing indisponible - verifiez le conteneur job-sourcing")

    st.divider()

    # -- Chargement dynamique des sites ---
    sources = get_spiders_disponibles()
    sources_dediees = {
        source_id: info
        for source_id, info in sources.items()
        if info.get("has_dedicated_folder", False) and info.get("active", True)
    }
    api_count = sum(
        1 for info in sources_dediees.values()
        if info.get("source_type") == "api"
    )
    scraping_count = len(sources_dediees) - api_count

    # -- Selection des spiders ---
    st.subheader(f"Sources dediees disponibles ({len(sources_dediees)})")
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.caption(f"Scraping dedie: {scraping_count}")
    with col_meta2:
        st.caption(f"API dediees: {api_count}")

    if not sources_dediees:
        st.warning("Aucune source dediee detectee depuis le registre.")
        return

    selected = []
    cols = st.columns(3)
    for i, (source_id, info) in enumerate(sources_dediees.items()):
        source_type = info.get("source_type", "scraping")
        provider = info.get("api_provider")
        type_label = "API" if source_type == "api" else "SCRAPING"
        provider_suffix = f" | {provider}" if provider else ""

        with cols[i % 3]:
            checked = st.checkbox(
                f"**{info['label']}** ({info['pays']}) [{type_label}{provider_suffix}]",
                value=True,
                key=f"source_{source_id}",
                help=info.get("description", ""),
            )
            if checked:
                selected.append(source_id)
            st.caption(info.get("description", ""))

    st.divider()

    # -- Options ---
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        full_crawl = st.checkbox("Mode crawl complet (plus lent, plus complet)", value=False)
    with col_opt2:
        auto_clean = False
        if DASHBOARD_MODE != "sourcing_only":
            auto_clean = st.checkbox("Lancer le nettoyage automatiquement apres", value=True)
        else:
            st.caption("Mode sourcing_only: nettoyage aval masque.")

    st.divider()

    # -- Boutons d'action ---
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

    with col_btn1:
        if st.button("Lancer le scraping", type="primary", use_container_width=True):
            _executer_scraping(selected, full_crawl, auto_clean)

    with col_btn2:
        if DASHBOARD_MODE != "sourcing_only" and st.button("Nettoyage seul", use_container_width=True):
            result = lancer_nettoyage(since_hours=24)
            if result.get("status") == "success":
                st.success(f"{result.get('cleaned_count', 0)} offre(s) nettoyee(s)")
            else:
                st.warning(f"Resultat: {result.get('detail', 'Pas de reponse')}")
        elif DASHBOARD_MODE == "sourcing_only":
            st.button("Nettoyage masque", disabled=True, use_container_width=True)

    with col_btn3:
        if st.button("Rafraichir", use_container_width=True):
            st.rerun()


def _executer_scraping(selected, full_crawl, auto_clean):
    """Execute le scraping en une seule requete avec tous les sites."""
    if not selected:
        st.error("Selectionnez au moins un site.")
        return

    st.info(f"Lancement du scraping sur {len(selected)} site(s)... (peut prendre quelques minutes)")
    progress = st.progress(0)

    # Envoyer tous les spiders en une seule requete
    result = lancer_scraping(selected, full=full_crawl)
    progress.progress(100)

    st.divider()
    st.subheader("Resultats du scraping")

    status = result.get("status", "inconnu")
    count = result.get("count", 0)
    errors = result.get("errors", 0)

    if status in ("success", "scheduled"):
        st.success(f"{count} offre(s) collectee(s) sur {len(selected)} site(s)")
        if errors > 0:
            st.warning(f"{errors} spider(s) en erreur")
    else:
        st.error(f"Erreur: {result.get('detail', 'Reponse inattendue')}")

    if auto_clean:
        st.divider()
        st.info("Lancement du nettoyage des donnees...")
        clean_result = lancer_nettoyage(since_hours=1)
        if clean_result.get("status") == "success":
            st.success(f"Nettoyage termine : {clean_result.get('cleaned_count', 0)} offre(s) traitee(s)")
        else:
            st.warning(f"Nettoyage : {clean_result.get('detail', 'Pas de reponse')}")
