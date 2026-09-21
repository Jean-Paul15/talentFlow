# Point d'entree principal - Dashboard TalentFlow
# Architecture modulaire : config / services / pages

import streamlit as st
from datetime import datetime

from config import DASHBOARD_MODE

st.set_page_config(
    page_title="TalentFlow - Supervision",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

def _build_pages():
    # Mode minimal: MinIO + Lake API + visualisation.
    if DASHBOARD_MODE == "lake_only":
        from views.lake_dashboard import page_lake_dashboard
        from views.stockage import page_stockage
        from views.architecture import page_architecture

        return {
            "Tableau de bord": page_lake_dashboard,
            "Stockage (API/Lake)": page_stockage,
            "Architecture": page_architecture,
        }

    # Mode demo: collecte -> stockage avec API uniquement.
    if DASHBOARD_MODE == "sourcing_only":
        from views.executive_dashboard import page_executive_dashboard
        from views.sourcing import page_sourcing
        from views.silver_cleaned import page_silver_cleaned
        from views.orchestration import page_orchestration
        from views.recherche import page_recherche
        from views.stockage import page_stockage
        from views.flux import page_flux
        from views.architecture import page_architecture

        return {
            "Tableau de bord": page_executive_dashboard,
            "Sourcing": page_sourcing,
            "Donnees nettoyees (MongoDB)": page_silver_cleaned,
            "Orchestration": page_orchestration,
            "Recherche / CV": page_recherche,
            "Stockage (API/Lake)": page_stockage,
            "Flux de donnees": page_flux,
            "Architecture": page_architecture,
        }

    # Mode complet.
    from views.tableau_de_bord import page_tableau_de_bord
    from views.sourcing import page_sourcing
    from views.silver_cleaned import page_silver_cleaned
    from views.recherche import page_recherche
    from views.statistiques import page_statistiques
    from views.stockage import page_stockage
    from views.flux import page_flux
    from views.orchestration import page_orchestration
    from views.architecture import page_architecture

    return {
        "Tableau de bord": page_tableau_de_bord,
        "Sourcing": page_sourcing,
        "Donnees nettoyees (MongoDB)": page_silver_cleaned,
        "Orchestration": page_orchestration,
        "Recherche": page_recherche,
        "Statistiques": page_statistiques,
        "Stockage": page_stockage,
        "Flux de donnees": page_flux,
        "Architecture": page_architecture,
    }


def main():
    pages = _build_pages()

    st.sidebar.title("TalentFlow")
    if DASHBOARD_MODE == "sourcing_only":
        st.sidebar.caption("Mode demo: collecte -> stockage")
    elif DASHBOARD_MODE == "lake_only":
        st.sidebar.caption("Mode demo: MinIO -> Lake API -> dashboard")
    else:
        st.sidebar.caption("Supervision complete du systeme")
    st.sidebar.divider()

    page = st.sidebar.radio("Navigation", list(pages.keys()))

    st.sidebar.divider()
    st.sidebar.caption(f"Actualise : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    st.sidebar.caption(f"Mode: {DASHBOARD_MODE}")
    if st.sidebar.button("Actualiser"):
        st.rerun()

    pages[page]()


if __name__ == "__main__":
    main()
