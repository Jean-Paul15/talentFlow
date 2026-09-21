# Page Orchestration - Horaires Airflow et gestion des sites
# Affichage dynamique des planifications par site

import streamlit as st

from services.orchestration import (
    get_schedule,
    get_sites_registry,
    get_sourcing_stats,
    get_orchestration_settings,
    update_orchestration_settings,
    list_airflow_dags,
    set_airflow_dag_pause,
    trigger_airflow_dag,
    statut_airflow,
    lancer_purge,
    lancer_purge_et_rescrape,
)
from services.cleaning import statut_nettoyage
from services.search_engine import search_engine_health, search_sync_status_api


# Couleurs par priorite
PRIORITY_COLORS = {
    1: "#22c55e",  # vert - haute
    2: "#3b82f6",  # bleu - moyenne
    3: "#f59e0b",  # orange - basse
    4: "#6366f1",  # violet - nocturne
}

PRIORITY_ICONS = {
    1: "!",
    2: "-",
    3: ".",
    4: "*",
}


def page_orchestration():
    st.header("Orchestration Airflow")
    st.caption(
        "Planification automatique du scraping - "
        "les horaires sont generes dynamiquement depuis le registre de sites"
    )

    # -- Statut Airflow ---
    col_airflow, col_stats = st.columns([1, 2])

    with col_airflow:
        airflow_status = statut_airflow()
        if airflow_status["status"] == "operationnel":
            st.success("Airflow operationnel")
        else:
            st.warning(
                "Airflow indisponible - "
                "lancez le profil orchestration dans Docker Compose"
            )

    with col_stats:
        stats = get_sourcing_stats()
        redis_info = stats.get("redis", {})
        minio_info = stats.get("minio", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Fingerprints Redis", redis_info.get("total_keys", 0))
        c2.metric("Bronze en attente", minio_info.get("bronze_pending_objects", minio_info.get("bronze_objects", 0)))
        c3.metric("Bucket", minio_info.get("bucket", "?"))

    st.divider()

    st.subheader("Etat du pipeline automatique")
    cleaning_status = statut_nettoyage()
    search_health = search_engine_health()
    search_sync = search_sync_status_api()
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Bronze en attente", cleaning_status.get("bronze_pending_objects", stats.get("minio", {}).get("bronze_pending_objects", 0)))
    p2.metric("Silver Mongo", cleaning_status.get("jobs_in_mongodb", 0))
    p3.metric("Docs indexés", search_health.get("doc_count", 0))
    p4.metric("Delta index", search_sync.get("delta_pending_count", 0) if not search_sync.get("error") else "-")
    p5.metric("Backend search", search_health.get("search_backend", "-"))

    st.caption(
        f"Cleaning LLM: {cleaning_status.get('llm_provider_primary', 'mistral')} "
        f"| Fallback extraction: {cleaning_status.get('llm_provider_fallback', 'ner_patterns')} "
        f"| Sync status: {search_sync.get('reason', '-') if isinstance(search_sync, dict) else '-'}"
    )

    if search_sync.get("error"):
        st.warning(f"Sync-status indisponible: {search_sync.get('detail', 'erreur inconnue')}")

    st.divider()

    # -- Programmation automatique ---
    st.subheader("Programmation automatique")
    settings = get_orchestration_settings()
    priority_schedule = settings.get("priority_schedule", {})

    p1 = priority_schedule.get("1", {})
    p2 = priority_schedule.get("2", {})
    p3 = priority_schedule.get("3", {})
    p4 = priority_schedule.get("4", {})

    with st.form("orchestration_schedule_form"):
        c1, c2 = st.columns(2)
        with c1:
            cron_p1 = st.text_input(
                "Cron P1 (haute)",
                value=p1.get("cron", "0 6,14,20 * * *"),
            )
            cron_p2 = st.text_input(
                "Cron P2 (moyenne)",
                value=p2.get("cron", "0 8,16 * * *"),
            )
        with c2:
            cron_p3 = st.text_input(
                "Cron P3 (basse)",
                value=p3.get("cron", "0 10 * * *"),
            )
            cron_p4 = st.text_input(
                "Cron P4 (nocturne)",
                value=p4.get("cron", "0 2 * * *"),
            )

        d1, d2, d3, d4 = st.columns(4)
        enabled_p1 = d1.checkbox("Activer P1", value=bool(p1.get("enabled", True)))
        enabled_p2 = d2.checkbox("Activer P2", value=bool(p2.get("enabled", True)))
        enabled_p3 = d3.checkbox("Activer P3", value=bool(p3.get("enabled", True)))
        enabled_p4 = d4.checkbox("Activer P4", value=bool(p4.get("enabled", True)))

        submitted = st.form_submit_button(
            "Enregistrer la programmation",
            type="primary",
        )

    if submitted:
        cron_payload = {
            "1": cron_p1.strip(),
            "2": cron_p2.strip(),
            "3": cron_p3.strip(),
            "4": cron_p4.strip(),
        }

        enabled_payload = {}
        for key, enabled in [
            ("1", enabled_p1),
            ("2", enabled_p2),
            ("3", enabled_p3),
            ("4", enabled_p4),
        ]:
            dag_id = priority_schedule.get(key, {}).get("dag_id")
            if dag_id:
                enabled_payload[dag_id] = bool(enabled)

        result = update_orchestration_settings(
            priority_crons=cron_payload,
            dag_enabled=enabled_payload,
        )
        if result.get("status") == "updated":
            st.success(
                "Programmation enregistree. Airflow appliquera les nouveaux crons automatiquement."
            )

            # Appliquer immediatement pause/reprise pour l'UI Airflow
            for dag_id, enabled in enabled_payload.items():
                set_airflow_dag_pause(dag_id, paused=not enabled)
        else:
            st.error(f"Erreur: {result.get('detail', 'mise a jour impossible')}")

    st.caption("Format cron attendu: `minute heure jour mois jour_semaine` (ex: `0 6,14,20 * * *`).")

    st.divider()

    # -- Pilotage DAG Airflow ---
    st.subheader("Pilotage des DAGs")
    dags_data = list_airflow_dags()
    dags = dags_data.get("dags", [])

    if dags:
        managed_dags = [
            dag for dag in dags
            if dag.get("dag_id", "").startswith("sourcing_")
            or dag.get("dag_id") == "talentflow_pipeline"
        ]
        for dag in managed_dags:
            dag_id = dag.get("dag_id", "?")
            paused = bool(dag.get("is_paused", False))
            next_run = dag.get("next_dagrun", "-")

            col_d1, col_d2, col_d3, col_d4 = st.columns([4, 2, 2, 2])
            col_d1.write(f"`{dag_id}`")
            col_d2.write("Pause" if paused else "Actif")
            col_d3.caption(f"Prochain: {next_run if next_run else '-'}")

            if col_d4.button("Lancer", key=f"trigger_{dag_id}"):
                trigger_result = trigger_airflow_dag(dag_id)
                if trigger_result.get("status") == "triggered":
                    st.success(f"DAG lance: {dag_id}")
                else:
                    st.error(f"Echec trigger: {trigger_result.get('detail', 'erreur')}")

            toggle_col1, toggle_col2 = st.columns([1, 5])
            action_label = "Activer" if paused else "Mettre en pause"
            if toggle_col1.button(action_label, key=f"toggle_{dag_id}"):
                pause_result = set_airflow_dag_pause(dag_id, paused=not paused)
                if pause_result.get("status") == "ok":
                    st.success(f"{dag_id}: etat mis a jour")
                else:
                    st.error(f"Echec pause/reprise: {pause_result.get('detail', 'erreur')}")
    else:
        st.info("DAGs Airflow non accessibles pour le moment.")

    st.divider()

    # -- Tableau des horaires par site ---
    schedule = get_schedule()
    sites_schedule = schedule.get("sites", [])
    dags_config = schedule.get("dags", {})

    if not sites_schedule:
        st.warning("Impossible de recuperer les horaires (service job-sourcing indisponible)")
        return

    st.subheader(f"Planification des {len(sites_schedule)} sites")

    # Regrouper par priorite
    by_priority = {}
    for site in sites_schedule:
        p = site["priority"]
        if p not in by_priority:
            by_priority[p] = []
        by_priority[p].append(site)

    # Afficher chaque groupe de priorite
    for priority in sorted(by_priority.keys()):
        sites_group = by_priority[priority]
        dag_info = dags_config.get(str(priority), {})
        color = PRIORITY_COLORS.get(priority, "#888")
        label = sites_group[0]["priority_label"]
        freq = sites_group[0]["frequency"]
        hours = sites_group[0]["hours"]
        cron = sites_group[0]["cron"]

        st.markdown(
            f"### Priorite {priority} : {label}"
        )

        # Bandeau d'horaires
        hours_display = " | ".join(
            [f"**{h}**" for h in hours]
        )
        st.markdown(
            f"Horaires de lancement : {hours_display} &nbsp;&nbsp; "
            f"Cron : `{cron}` &nbsp;&nbsp; "
            f"Frequence : {freq}"
        )

        # Tableau des sites
        cols_header = st.columns([3, 3, 2, 2, 2])
        cols_header[0].markdown("**Site**")
        cols_header[1].markdown("**URL**")
        cols_header[2].markdown("**Pays**")
        cols_header[3].markdown("**Spider**")
        cols_header[4].markdown("**Categorie**")

        for site in sites_group:
            cols = st.columns([3, 3, 2, 2, 2])
            cols[0].write(site["label"])
            cols[1].caption(site["url"][:50] + ("..." if len(site["url"]) > 50 else ""))
            cols[2].write(site["pays"])
            spider_name = site["spider"]
            if spider_name == "deep_crawler":
                cols[3].markdown(f"*{spider_name}*")
            else:
                cols[3].write(spider_name)
            cols[4].write(site["category"])

        # Info DAG
        if dag_info:
            spiders = dag_info.get("spiders", [])
            total = dag_info.get("total_sites", 0)
            st.caption(
                f"DAG Airflow : {total} site(s) via {', '.join(spiders)}"
            )

        st.divider()

    # -- Resume visuel des horaires ---
    st.subheader("Timeline journaliere")
    _render_timeline(by_priority)

    st.divider()

    # -- Actions ---
    st.subheader("Actions rapides")
    col_a1, col_a2, col_a3 = st.columns(3)

    with col_a1:
        if st.button("Purger tout (Redis + MinIO)", type="secondary"):
            result = lancer_purge()
            if result.get("status") == "purged":
                st.success("Purge terminee avec succes")
                st.json(result)
            else:
                st.error(f"Erreur : {result.get('detail', 'Inconnue')}")

    with col_a2:
        if st.button("Purger + Relancer tout", type="primary"):
            result = lancer_purge_et_rescrape()
            if result.get("status") == "purged_and_scheduled":
                st.success("Purge + relance programmee")
                st.json(result)
            else:
                st.error(f"Erreur : {result.get('detail', 'Inconnue')}")

    with col_a3:
        if st.button("Rafraichir les horaires"):
            st.rerun()

    # -- Registre complet ---
    st.divider()
    st.subheader("Registre complet des sites")
    registry = get_sites_registry()

    if registry.get("total", 0) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total sites", registry["total"])
        c2.metric("Avec spider dedie", registry.get("with_spider", 0))
        c3.metric("Via Deep Crawler", registry.get("deep_crawler", 0))

        with st.expander("Voir tous les sites enregistres"):
            for site_id, info in registry.get("sites", {}).items():
                st.markdown(
                    f"- **{info['label']}** ({info['pays']}) "
                    f"-- spider: `{info['spider']}` "
                    f"-- priorite: {info['priority']}"
                )


def _render_timeline(by_priority: dict):
    """Affiche une timeline textuelle des heures de lancement."""
    # Construire la grille horaire
    hours_grid = {}
    for priority, sites in by_priority.items():
        if not sites:
            continue
        for h in sites[0]["hours"]:
            if h not in hours_grid:
                hours_grid[h] = []
            count = len(sites)
            label = f"P{priority}"
            hours_grid[h].append(f"{label} ({count} sites)")

    if not hours_grid:
        st.info("Aucun horaire disponible")
        return

    # Trier par heure
    sorted_hours = sorted(hours_grid.keys())

    cols = st.columns(len(sorted_hours))
    for i, hour in enumerate(sorted_hours):
        with cols[i]:
            st.markdown(f"**{hour}**")
            for entry in hours_grid[hour]:
                st.caption(entry)
