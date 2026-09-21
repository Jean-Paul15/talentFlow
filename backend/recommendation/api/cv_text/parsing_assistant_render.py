"""Rendering helpers for structured assistant payloads."""

from __future__ import annotations

__all__ = ["_render_assistant_structured"]


def _render_assistant_structured(payload: dict) -> str:
    lines = ["Résumé du profil :", str(payload.get("profile_summary") or "").strip(), "", "Forces :"]

    for item in payload.get("strengths") or []:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Points à corriger :")
    for item in payload.get("gaps") or []:
        lines.append(f"- {item}")

    lines.append("")
    if str(payload.get("mode") or "") == "no_match":
        reason = str(payload.get("reason_if_no_match") or "").strip()
        lines.append("Aucune offre recommandée :")
        lines.append(reason or "Aucune offre réellement pertinente n'a été retenue pour ce profil.")
    else:
        lines.append("Offres recommandées :")
        for idx, reco in enumerate(payload.get("recommended_jobs") or [], start=1):
            lines.append(f"{idx}. {reco['title']}")
            lines.append(f"   Pourquoi : {reco['why']}")
            lines.append(f"   Lien : {reco['url']}")
            lines.append(f"   Amélioration CV : {reco['cv_improvement']}")

    score_explanation = str(payload.get("score_explanation") or "").strip()
    if score_explanation:
        lines.append("")
        lines.append("Progression de score :")
        lines.append(score_explanation)

    playbooks = payload.get("offer_playbooks") or []
    if isinstance(playbooks, list) and playbooks:
        lines.append("")
        lines.append("Playbooks par offre :")
        for idx, item in enumerate(playbooks[:3], start=1):
            if not isinstance(item, dict):
                continue
            rewrite = item.get("rewrite")
            rewrite = rewrite if isinstance(rewrite, dict) else {}
            title = str(item.get("title") or "").strip()
            delta = str(item.get("cv_delta") or "").strip()
            why_fit = str(item.get("why_fit") or "").strip()
            target_title = str(rewrite.get("target_title") or "").strip()
            target_summary = str(rewrite.get("target_summary") or "").strip()
            evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []

            lines.append(f"{idx}. {title}")
            if why_fit:
                lines.append(f"   Pourquoi cette offre : {why_fit}")
            if delta:
                lines.append(f"   Écart CV : {delta}")
            if target_title:
                lines.append(f"   Titre cible : {target_title}")
            if target_summary:
                lines.append(f"   Résumé cible : {target_summary}")
            if evidence:
                lines.append(f"   Preuves CV : {', '.join(str(x) for x in evidence[:3])}")

    lines.append("")
    lines.append("Actions immédiates :")
    for idx, item in enumerate(payload.get("actions") or [], start=1):
        lines.append(f"{idx}. {item}")

    return "\n".join(lines)
