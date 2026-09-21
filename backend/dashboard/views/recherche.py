# Page Recherche - Demo Search Engine (retrieval + rerank + evaluation)

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st
from pypdf import PdfReader

from config import RECOMMENDATION_URL, SEARCH_ENGINE_URL
from services.recommendation import (
    recommendation_health,
    recommendation_llm_runtime,
    recommend_from_cv_text_api,
)
from services.search_engine import (
    search_engine_health,
    search_jobs_api,
    compare_rerank_api,
    compare_modes_api,
    evaluate_search_api,
    evaluate_search_batch_api,
    get_rerank_policy_api,
    set_rerank_policy_manual_api,
    set_rerank_policy_auto_api,
    vector_preview_api,
)


def _extract_uploaded_cv_text(uploaded_file) -> Dict[str, Any]:
    file_name = str(getattr(uploaded_file, "name", "cv.pdf") or "cv.pdf")
    suffix = Path(file_name).suffix.lower()
    raw = uploaded_file.getvalue()

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(raw))
        pages = []
        for page in reader.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(page_text)
        text = "\n\n".join(pages).strip()
        strategy = "pdf_pypdf"
    elif suffix in {".txt", ".md"}:
        text = raw.decode("utf-8", errors="ignore").strip()
        strategy = "plain_text"
    else:
        raise ValueError("Format non supporté. Utilise un fichier PDF ou TXT.")

    if len(text) < 20:
        raise ValueError("Texte extrait trop court. Vérifie que le PDF n'est pas scanné en image.")

    return {
        "file_name": file_name,
        "mime_type": getattr(uploaded_file, "type", "") or "",
        "strategy": strategy,
        "extracted_chars": len(text),
        "text": text,
    }


def _result_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for idx, r in enumerate(results, start=1):
        rows.append(
            {
                "Rank": idx,
                "ID": str(r.get("id", "")),
                "Titre": r.get("title", "") or "",
                "Entreprise": r.get("company", "") or "",
                "Lieu": r.get("location", "") or "",
                "Score": round(float(r.get("score") or 0.0), 4),
                "Base": round(float(r.get("base_score") or 0.0), 4) if r.get("base_score") is not None else None,
                "Rerank": round(float(r.get("rerank_score") or 0.0), 4) if r.get("rerank_score") is not None else None,
                "URL": r.get("source_url", "") or "",
            }
        )
    return rows


def _render_result_list(results: List[Dict[str, Any]], title: str):
    st.subheader(title)
    if not results:
        st.info("Aucun resultat.")
        return
    df = pd.DataFrame(_result_rows(results))
    st.dataframe(df, use_container_width=True, hide_index=True)

    for r in results[:5]:
        label = f"{r.get('title', 'Sans titre')} - {r.get('company', '')}"
        with st.expander(label):
            st.write(f"**ID:** `{r.get('id', '')}`")
            st.write(f"**Score:** `{round(float(r.get('score') or 0.0), 4)}`")
            if r.get("base_score") is not None:
                st.write(f"**Base score:** `{round(float(r.get('base_score') or 0.0), 4)}`")
            if r.get("rerank_score") is not None:
                st.write(f"**Rerank score:** `{round(float(r.get('rerank_score') or 0.0), 4)}`")
            st.write(f"**Localisation:** {r.get('location', '')}")
            st.write(f"**Contrat:** {r.get('contract_type', '')}")
            desc = (r.get("description") or "").strip()
            if desc:
                st.write(desc)
            if r.get("source_url"):
                st.link_button("Voir l'offre", r["source_url"])


def _metric_from_eval(eval_out: Dict[str, Any], family: str, k: str) -> float:
    return float(eval_out.get(family, {}).get(str(k), 0.0))


def _render_assistant_structured_panel(payload: Dict[str, Any]) -> None:
    mode = str(payload.get("mode") or "").strip().lower()
    profile_summary = str(payload.get("profile_summary") or "").strip()
    strengths = payload.get("strengths") or []
    gaps = payload.get("gaps") or []
    actions = payload.get("actions") or []
    recos = payload.get("recommended_jobs") or []
    reason = str(payload.get("reason_if_no_match") or "").strip()

    st.subheader("Synthèse structurée")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"**Mode:** `{mode or '-'}`")
        if profile_summary:
            st.write(profile_summary)
    with c2:
        if mode == "no_match":
            st.warning("Aucun match crédible")
        elif mode == "match":
            st.success("Match trouvé")
        else:
            st.info("Mode indéfini")

    left, right = st.columns(2)
    with left:
        st.markdown("**Forces**")
        for item in strengths[:5]:
            st.write(f"- {item}")
    with right:
        st.markdown("**Gaps**")
        for item in gaps[:5]:
            st.write(f"- {item}")

    st.markdown("**Actions immédiates**")
    for idx, item in enumerate(actions[:6], start=1):
        st.write(f"{idx}. {item}")

    if mode == "no_match":
        st.info(reason or "Aucune offre suffisamment pertinente pour le moment.")
        return

    st.markdown("**Offres recommandées (assistantStructured)**")
    if not recos:
        st.warning("Le mode est `match` mais aucune offre structurée n'a été fournie.")
        return
    for idx, rec in enumerate(recos[:5], start=1):
        with st.expander(f"{idx}. {rec.get('title', 'Sans titre')}"):
            st.write(f"**Job ID:** `{rec.get('job_id', '')}`")
            st.write(f"**Pourquoi:** {rec.get('why', '')}")
            st.write(f"**Amélioration CV:** {rec.get('cv_improvement', '')}")
            url = str(rec.get("url") or "").strip()
            if url:
                st.link_button("Voir l'offre", url)


def _render_ats_lite(ats_lite: Dict[str, Any]) -> None:
    if not ats_lite:
        return
    st.subheader("ATS-lite")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Global", int(ats_lite.get("overall_score", 0) or 0))
    c2.metric("Structure", int(ats_lite.get("structure_score", 0) or 0))
    c3.metric("Alignement", int(ats_lite.get("alignment_score", 0) or 0))
    c4.metric("Preuves", int(ats_lite.get("evidence_score", 0) or 0))
    if ats_lite.get("readiness_label"):
        st.caption(f"Readiness: {ats_lite.get('readiness_label')}")
    if ats_lite.get("summary"):
        st.write(str(ats_lite.get("summary")))

    mk = ats_lite.get("matched_keywords") or []
    miss = ats_lite.get("missing_keywords") or []
    if mk:
        st.markdown("**Mots-clés alignés**: " + ", ".join([str(x) for x in mk[:12]]))
    if miss:
        st.markdown("**Mots-clés manquants**: " + ", ".join([str(x) for x in miss[:12]]))


def _render_cv_recommendation(out: Dict[str, Any]) -> None:
    if out.get("error"):
        st.error(f"Erreur recommandation: {out.get('detail', 'inconnue')}")
        return

    cv_analysis = out.get("cv_analysis") or {}
    jobs = out.get("jobs") or []
    assistant_structured = out.get("assistant_structured") or {}
    ats_lite = out.get("ats_lite") or {}
    llm_status = str(out.get("llm_status") or "-")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Résultats", int(out.get("total_results", 0) or 0))
    m2.metric("LLM", "Oui" if out.get("llm_used") else "Non")
    m3.metric("Statut LLM", llm_status)
    m4.metric("Provider", str(out.get("llm_provider") or "-"))
    m5.metric("Expérience", cv_analysis.get("experience_years") if cv_analysis.get("experience_years") is not None else "-")
    st.caption(f"Modèle: {str(out.get('llm_model') or '-')}")
    if out.get("llm_error"):
        st.caption(f"Erreur LLM: {str(out.get('llm_error'))}")

    skills = cv_analysis.get("skills") or []
    if skills:
        st.markdown("**Compétences détectées:** " + ", ".join([str(s) for s in skills[:20]]))
    if cv_analysis.get("education_level"):
        st.caption(f"Niveau détecté: {cv_analysis.get('education_level')}")

    if assistant_structured:
        _render_assistant_structured_panel(assistant_structured)
    _render_ats_lite(ats_lite)

    assistant_message = str(out.get("assistant_message") or "").strip()
    if assistant_message:
        with st.expander("Texte assistant (fallback/backward-compat)", expanded=False):
            st.markdown(assistant_message.replace("\n", "  \n"))

    _render_result_list(jobs, "Offres recommandées")


def page_recherche():
    st.header("Recherche IA / Evaluation Retrieval")
    st.caption(
        "Demo search-engine: retrieval, CV -> recommandation, compare avant/apres reranker, "
        "et evaluation nDCG@k."
    )

    health = search_engine_health()
    reco_health = recommendation_health()
    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Search Engine", "OK" if health.get("status") == "healthy" else "KO")
    top2.metric("Backend", str(health.get("search_backend", "unknown")))
    top3.metric("Index docs", int(health.get("doc_count", 0) or 0))
    top4.metric("Rerank defaut", "ON" if health.get("reranker_enabled_default") else "OFF")
    st.caption(f"Base URL: {SEARCH_ENGINE_URL}")
    st.caption(f"Recommendation URL: {RECOMMENDATION_URL} | Statut: {'OK' if reco_health.get('status') in {'ready', 'healthy'} else 'KO'}")

    policy_snapshot = get_rerank_policy_api(history_limit=10)

    with st.expander("Parametres de demo", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            query = st.text_input(
                "Requete",
                value=st.session_state.get("tf_search_query", "data analyst python"),
                placeholder="ex: backend fastapi python",
                key="tf_search_query",
            )
        with c2:
            limit = st.number_input("Limit final", min_value=1, max_value=50, value=10, step=1)
        with c3:
            candidate_pool_size = st.number_input("Pool initial", min_value=1, max_value=200, value=30, step=1)
        with c4:
            rerank_top_k = st.number_input("Rerank top-k", min_value=1, max_value=200, value=20, step=1)

    tab_search, tab_cv, tab_compare, tab_modes, tab_vectors, tab_eval, tab_eval_batch = st.tabs(
        ["Recherche", "CV / PDF", "Compare Rerank", "Compare Modes", "Vecteurs", "Eval nDCG", "Eval Batch"]
    )

    with tab_search:
        col_a, col_b = st.columns([1, 1])
        rerank_for_search = col_a.toggle("Rerank sur /search", value=False)
        run_search = col_b.button("Lancer /search", use_container_width=True)
        if run_search and query.strip():
            with st.spinner("Recherche..."):
                out = search_jobs_api(
                    query.strip(),
                    limit=int(limit),
                    rerank=bool(rerank_for_search),
                    candidate_pool_size=int(candidate_pool_size),
                    rerank_top_k=int(rerank_top_k),
                )
            st.session_state["tf_last_search_out"] = out

        search_out = st.session_state.get("tf_last_search_out")
        if search_out:
            meta_cols = st.columns(5)
            meta_cols[0].metric("Backend", str(search_out.get("backend", "-")))
            meta_cols[1].metric("Total", int(search_out.get("total", 0) or 0))
            meta_cols[2].metric("Reranked", "Oui" if search_out.get("reranked") else "Non")
            meta_cols[3].metric("Mode", str(search_out.get("search_mode", "-") or "-"))
            meta_cols[4].metric("Hybrid", str(search_out.get("hybrid_strategy", "-") or "-"))
            _render_result_list(search_out.get("results", []), "Resultats /search")

    with tab_cv:
        st.subheader("Import CV PDF et recommandation")
        st.caption(
            "Le dashboard extrait le texte du fichier côté Streamlit, puis appelle le service "
            "de recommandation existant. Utilise PDF texte natif, ou TXT si besoin."
        )

        st.session_state.setdefault("tf_cv_reco_text", "")
        st.session_state.setdefault("tf_cv_upload_meta", None)

        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        cv_top_k = rc1.slider("Top K", min_value=1, max_value=10, value=5, step=1)
        cv_location = rc2.text_input("Filtre lieu", value="", key="tf_cv_filter_location")
        cv_contract = rc3.text_input("Filtre contrat", value="", key="tf_cv_filter_contract")
        cv_use_llm = rc4.toggle("Synthèse LLM", value=True, key="tf_cv_use_llm")
        cv_llm_model = rc5.text_input(
            "Modèle (optionnel)",
            value="",
            key="tf_cv_llm_model",
            placeholder="ex: gemini:gemini-2.5-flash ou deepseek:deepseek-chat",
        )

        runtime_c1, runtime_c2 = st.columns([1, 4])
        if runtime_c1.button("Runtime LLM", use_container_width=True):
            st.session_state["tf_cv_llm_runtime"] = recommendation_llm_runtime()
        runtime_snapshot = st.session_state.get("tf_cv_llm_runtime")
        if runtime_snapshot:
            if runtime_snapshot.get("error"):
                runtime_c2.error(f"Runtime indisponible: {runtime_snapshot.get('detail', 'erreur')}")
            else:
                runtime_c2.json(runtime_snapshot, expanded=False)

        cc1, cc2 = st.columns([2, 1])
        uploaded_file = cc1.file_uploader(
            "Importer un CV",
            type=["pdf", "txt"],
            help="PDF texte natif recommandé. Les PDF scannés en image ne seront pas bien extraits.",
            key="tf_cv_pdf_uploader",
        )
        extract_clicked = cc2.button("Extraire le texte", use_container_width=True)

        if extract_clicked:
            if not uploaded_file:
                st.warning("Choisis un fichier PDF ou TXT.")
            else:
                try:
                    extracted = _extract_uploaded_cv_text(uploaded_file)
                    st.session_state["tf_cv_reco_text"] = extracted["text"]
                    st.session_state["tf_cv_upload_meta"] = extracted
                    st.success(
                        f"Extraction réussie: {extracted['file_name']} | "
                        f"{extracted['extracted_chars']} caractères"
                    )
                except Exception as err:
                    st.error(f"Extraction impossible: {err}")

        meta = st.session_state.get("tf_cv_upload_meta")
        if meta:
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Fichier", meta.get("file_name", "-"))
            mc2.metric("Stratégie", meta.get("strategy", "-"))
            mc3.metric("Texte extrait", int(meta.get("extracted_chars", 0) or 0))

        st.text_area(
            "Texte du CV",
            key="tf_cv_reco_text",
            height=280,
            placeholder="Importe un PDF ou colle ici le texte du CV.",
        )

        act1, act2 = st.columns([1, 1])
        run_cv_reco = act1.button("Obtenir la recommandation", type="primary", use_container_width=True)
        clear_cv_text = act2.button("Vider", use_container_width=True)
        if clear_cv_text:
            st.session_state["tf_cv_reco_text"] = ""
            st.session_state["tf_cv_upload_meta"] = None
            st.session_state.pop("tf_cv_recommendation_out", None)
            st.rerun()

        if run_cv_reco:
            cv_text = str(st.session_state.get("tf_cv_reco_text") or "").strip()
            if len(cv_text) < 10:
                st.warning("Le texte du CV est trop court.")
            else:
                with st.spinner("Analyse du CV et recommandation..."):
                    reco_out = recommend_from_cv_text_api(
                        cv_text=cv_text,
                        file_name=(meta or {}).get("file_name", "cv.pdf"),
                        top_k=int(cv_top_k),
                        location=cv_location.strip() or None,
                        contract_type=cv_contract.strip() or None,
                        use_llm=bool(cv_use_llm),
                        llm_model=cv_llm_model.strip() or None,
                    )
                st.session_state["tf_cv_recommendation_out"] = reco_out

        reco_out = st.session_state.get("tf_cv_recommendation_out")
        if reco_out:
            _render_cv_recommendation(reco_out)

    with tab_compare:
        if st.button("Comparer baseline vs rerank", type="primary", use_container_width=True) and query.strip():
            with st.spinner("Comparaison rerank..."):
                compare_out = compare_rerank_api(
                    query.strip(),
                    limit=int(limit),
                    candidate_pool_size=int(candidate_pool_size),
                    rerank_top_k=int(rerank_top_k),
                )
            st.session_state["tf_compare_out"] = compare_out

        compare_out = st.session_state.get("tf_compare_out")
        if compare_out:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Backend", str(compare_out.get("backend", "-")))
            m2.metric("Baseline", int(compare_out.get("baseline_total", 0) or 0))
            m3.metric("Reranked", int(compare_out.get("reranked_total", 0) or 0))
            m4.metric("Pool", int(compare_out.get("candidate_pool_size", 0) or 0))

            baseline = compare_out.get("baseline", []) or []
            reranked = compare_out.get("reranked", []) or []
            left, right = st.columns(2)
            with left:
                _render_result_list(baseline, "Baseline")
            with right:
                _render_result_list(reranked, "Apres Rerank")

            base_ids = [str(r.get("id")) for r in baseline if r.get("id") is not None]
            rerank_ids = [str(r.get("id")) for r in reranked if r.get("id") is not None]
            moved = sum(1 for i, doc_id in enumerate(rerank_ids) if i < len(base_ids) and doc_id != base_ids[i])
            st.info(f"Elements repositionnes dans le top-{min(len(base_ids), len(rerank_ids))}: {moved}")

    with tab_modes:
        st.caption("Comparaison 3 modes: Dense only vs Hybrid RRF vs Hybrid RRF + Rerank")
        if st.button("Comparer dense / hybrid / rerank", type="primary", use_container_width=True) and query.strip():
            with st.spinner("Comparaison des modes..."):
                modes_out = compare_modes_api(
                    query.strip(),
                    limit=int(limit),
                    candidate_pool_size=int(candidate_pool_size),
                    rerank_top_k=int(rerank_top_k),
                )
            st.session_state["tf_compare_modes_out"] = modes_out

        modes_out = st.session_state.get("tf_compare_modes_out")
        if modes_out:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Dense", int(modes_out.get("dense_total", 0) or 0))
            m2.metric("Hybrid", int(modes_out.get("hybrid_total", 0) or 0))
            m3.metric("Hybrid+Rerank", int(modes_out.get("hybrid_reranked_total", 0) or 0))
            m4.metric("Pool", int(modes_out.get("candidate_pool_size", 0) or 0))

            c1, c2, c3 = st.columns(3)
            with c1:
                _render_result_list(modes_out.get("dense", []) or [], "Dense only")
            with c2:
                _render_result_list(modes_out.get("hybrid", []) or [], "Hybrid RRF")
            with c3:
                _render_result_list(modes_out.get("hybrid_reranked", []) or [], "Hybrid + Rerank")

    with tab_vectors:
        st.caption("Projection 2D d'un echantillon de vecteurs stockes dans Qdrant.")
        vc1, vc2, vc3 = st.columns(3)
        vector_limit = vc1.slider("Nb points", min_value=20, max_value=300, value=120, step=20)
        vector_source = vc2.text_input("Filtre source", value="")
        vector_country = vc3.text_input("Filtre pays", value="")

        if st.button("Charger les vecteurs", use_container_width=True):
            with st.spinner("Chargement des vecteurs..."):
                vector_out = vector_preview_api(
                    limit=int(vector_limit),
                    source_name=vector_source.strip() or None,
                    country=vector_country.strip() or None,
                )
            st.session_state["tf_vector_preview_out"] = vector_out

        vector_out = st.session_state.get("tf_vector_preview_out")
        if vector_out:
            if vector_out.get("error"):
                st.error(f"Erreur preview vecteurs: {vector_out.get('detail', 'inconnue')}")
            else:
                points = vector_out.get("points", []) or []
                st.metric("Points projetes", int(vector_out.get("count", 0) or 0))
                if points:
                    df = pd.DataFrame(points)
                    fig = px.scatter(
                        df,
                        x="x",
                        y="y",
                        color="source_name" if "source_name" in df.columns else None,
                        hover_data=["title", "company", "location", "country", "contract_type", "quality_score", "freshness_days", "is_stale"],
                        height=520,
                    )
                    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(
                        df[["title", "company", "location", "country", "source_name", "posted_date", "quality_score", "freshness_days", "is_stale", "x", "y"]],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Aucun point vectoriel disponible avec ces filtres.")

    with tab_eval:
        compare_out = st.session_state.get("tf_compare_out")
        if not compare_out:
            st.info("Lance d'abord l'onglet 'Compare Rerank' pour selectionner des IDs pertinents.")
        else:
            candidate_ids = []
            seen = set()
            for section in ("baseline", "reranked"):
                for r in compare_out.get(section, []) or []:
                    rid = str(r.get("id")) if r.get("id") is not None else None
                    if rid and rid not in seen:
                        seen.add(rid)
                        candidate_ids.append(rid)

            relevant_ids = st.multiselect(
                "IDs pertinents (jugement binaire)",
                options=candidate_ids,
                default=candidate_ids[: min(3, len(candidate_ids))],
                key="tf_eval_relevant_ids",
            )
            k_values_text = st.text_input("k values", value="5,10")
            if st.button("Evaluer /search/evaluate", use_container_width=True):
                try:
                    k_values = [int(x.strip()) for x in k_values_text.split(",") if x.strip()]
                except ValueError:
                    st.error("k values invalide (ex: 5,10)")
                    k_values = []
                if not k_values:
                    st.stop()
                with st.spinner("Evaluation..."):
                    eval_out = evaluate_search_api(
                        query=st.session_state.get("tf_search_query", query).strip(),
                        relevant_ids=[str(x) for x in relevant_ids],
                        limit=int(limit),
                        candidate_pool_size=int(candidate_pool_size),
                        rerank_top_k=int(rerank_top_k),
                        k_values=k_values,
                    )
                st.session_state["tf_eval_out"] = eval_out

        eval_out = st.session_state.get("tf_eval_out")
        if eval_out:
            if eval_out.get("error"):
                st.error(f"Erreur evaluation: {eval_out.get('detail', 'inconnue')}")
            else:
                st.success(f"Jugements: {eval_out.get('judged_count', 0)} | backend={eval_out.get('backend', '-')}")
                baseline = eval_out.get("baseline", {}) or {}
                reranked = eval_out.get("reranked", {}) or {}
                ndcg_base = baseline.get("ndcg", {}) or {}
                ndcg_rer = reranked.get("ndcg", {}) or {}

                chart_rows = []
                for k in sorted(set(ndcg_base.keys()) | set(ndcg_rer.keys()), key=lambda x: int(x)):
                    chart_rows.append({"k": f"nDCG@{k}", "Systeme": "Baseline", "Score": float(ndcg_base.get(k, 0.0))})
                    chart_rows.append({"k": f"nDCG@{k}", "Systeme": "Rerank", "Score": float(ndcg_rer.get(k, 0.0))})
                if chart_rows:
                    fig = px.bar(pd.DataFrame(chart_rows), x="k", y="Score", color="Systeme", barmode="group")
                    fig.update_layout(height=320, margin=dict(t=10, l=10, r=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MRR baseline", f"{float(baseline.get('mrr', 0.0)):.3f}")
                c2.metric("MRR rerank", f"{float(reranked.get('mrr', 0.0)):.3f}")
                gain = float(reranked.get("mrr", 0.0) or 0.0) - float(baseline.get("mrr", 0.0) or 0.0)
                c3.metric("Gain MRR", f"{gain:+.3f}")
                k10 = "10" if "10" in ndcg_rer else (next(iter(ndcg_rer.keys())) if ndcg_rer else None)
                c4.metric("nDCG cible", f"{float(ndcg_rer.get(k10, 0.0)):.3f}" if k10 else "-")

                st.write("**Baseline IDs**")
                st.code(", ".join(eval_out.get("baseline_ids", [])[:20]), language=None)
                st.write("**Reranked IDs**")
                st.code(", ".join((eval_out.get("reranked_ids") or [])[:20]), language=None)

    with tab_eval_batch:
        st.caption("Colle un JSON de cas pour benchmark soutenance (multi-requetes).")
        default_cases = [
            {
                "query": "data analyst python",
                "relevant_ids": st.session_state.get("tf_eval_relevant_ids", [])[:2] if st.session_state.get("tf_eval_relevant_ids") else [],
            },
            {
                "query": "backend fastapi python",
                "relevant_ids": [],
            },
        ]
        payload_text = st.text_area(
            "Payload cases (liste JSON)",
            value=json.dumps(default_cases, ensure_ascii=False, indent=2),
            height=220,
        )
        k_values_batch = st.text_input("k values batch", value="5,10")
        if st.button("Lancer /search/evaluate-batch", use_container_width=True):
            try:
                cases = json.loads(payload_text)
                if not isinstance(cases, list):
                    raise ValueError("Le JSON doit etre une liste de cas.")
                k_values = [int(x.strip()) for x in k_values_batch.split(",") if x.strip()]
                if not k_values:
                    raise ValueError("k values vide")
            except Exception as err:
                st.error(f"Payload invalide: {err}")
            else:
                with st.spinner("Evaluation batch..."):
                    batch_out = evaluate_search_batch_api(
                        cases=cases,
                        limit=int(limit),
                        candidate_pool_size=int(candidate_pool_size),
                        rerank_top_k=int(rerank_top_k),
                        k_values=k_values,
                    )
                st.session_state["tf_eval_batch_out"] = batch_out

        batch_out = st.session_state.get("tf_eval_batch_out")
        if batch_out:
            if batch_out.get("error"):
                st.error(f"Erreur batch: {batch_out.get('detail', 'inconnue')}")
            else:
                summary = batch_out.get("summary", {}) or {}
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Cas", int(summary.get("cases_evaluated", 0) or 0))
                c2.metric("Skips", int(summary.get("cases_skipped", 0) or 0))
                c3.metric("Gain MRR", f"{float(summary.get('mrr_gain_abs', 0.0)):+.3f}")
                c4.metric("Gain MRR %", f"{float(summary.get('mrr_gain_pct', 0.0)):+.1f}%")

                base_ndcg = summary.get("mean_baseline_ndcg", {}) or {}
                rer_ndcg = summary.get("mean_reranked_ndcg", {}) or {}
                rows = []
                for k in sorted(set(base_ndcg.keys()) | set(rer_ndcg.keys()), key=lambda x: int(x)):
                    rows.append({"Metric": f"nDCG@{k}", "Systeme": "Baseline", "Score": float(base_ndcg.get(k, 0.0))})
                    rows.append({"Metric": f"nDCG@{k}", "Systeme": "Rerank", "Score": float(rer_ndcg.get(k, 0.0))})
                if rows:
                    fig = px.bar(pd.DataFrame(rows), x="Metric", y="Score", color="Systeme", barmode="group")
                    fig.update_layout(height=320, margin=dict(t=10, l=10, r=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)

                st.json(summary)
                if batch_out.get("cases"):
                    df_cases = pd.DataFrame(
                        [
                            {
                                "Query": c.get("query", ""),
                                "Judged": c.get("judged_count", 0),
                                "MRR base": (c.get("baseline") or {}).get("mrr", 0.0),
                                "MRR rerank": (c.get("reranked") or {}).get("mrr", 0.0),
                            }
                            for c in batch_out.get("cases", [])
                        ]
                    )
                    st.dataframe(df_cases, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Politique Auto-Rerank")

        current_policy = batch_out.get("rerank_policy") if batch_out and isinstance(batch_out, dict) else None
        if not current_policy or isinstance(current_policy, list):
            current_policy = policy_snapshot
        if not current_policy:
            current_policy = {"error": True, "detail": "policy indisponible"}

        if current_policy.get("error"):
            st.error(f"Policy indisponible: {current_policy.get('detail', 'erreur inconnue')}")
        else:
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Mode", str(current_policy.get("mode", "-")))
            p2.metric("Rerank defaut", "ON" if current_policy.get("enabled_default") else "OFF")
            p3.metric("History", int(current_policy.get("history_size", 0) or 0))
            p4.metric("k cible", int(current_policy.get("target_ndcg_k", 0) or 0))

            a, b, c = st.columns(3)
            if a.button("Mode AUTO", use_container_width=True):
                updated = set_rerank_policy_auto_api()
                st.session_state["tf_rerank_policy_state"] = updated
                st.rerun()
            if b.button("Mode MANUAL OFF", use_container_width=True):
                updated = set_rerank_policy_manual_api(False)
                st.session_state["tf_rerank_policy_state"] = updated
                st.rerun()
            if c.button("Mode MANUAL ON", use_container_width=True):
                updated = set_rerank_policy_manual_api(True)
                st.session_state["tf_rerank_policy_state"] = updated
                st.rerun()

            history = current_policy.get("history") or []
            if history:
                hist_df = pd.DataFrame(history)
                if "timestamp" in hist_df.columns:
                    hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"], errors="coerce")
                    hist_df = hist_df.sort_values("timestamp")
                for col in ("ndcg_gain_abs", "mrr_gain_abs"):
                    if col not in hist_df.columns:
                        hist_df[col] = 0.0
                fig = px.line(
                    hist_df,
                    x="timestamp",
                    y=["ndcg_gain_abs", "mrr_gain_abs"],
                    markers=True,
                    title="Gains rerank (fenêtres batch)",
                )
                fig.update_layout(height=320, margin=dict(t=40, l=10, r=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(hist_df.tail(20), use_container_width=True, hide_index=True)
