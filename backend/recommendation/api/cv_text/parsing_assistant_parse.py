"""Parsing and coercion helpers for structured assistant payloads."""

from __future__ import annotations

import json
import re

from services.cv_analyzer import extract_skills_from_text

from .models import CVAnalysisResult, RecommendedJobPreview
from .parsing_assistant_defaults import _default_actions, _default_gaps, _default_profile_summary, _default_strengths
from .parsing_core import (
    _build_default_offer_playbook,
    _build_default_score_explanation,
    _fallback_job_why,
    _no_match_reason,
    _normalize_skill_name,
    _suggest_cv_improvement_for_job,
)
from .text_utils import _canonicalize_url, _fold_text

__all__ = ["_parse_json_blob", "_coerce_assistant_structured", "_parse_assistant_structured"]

_GENERIC_ACTION_PATTERNS = (
    "adapte ton cv",
    "adapter le cv",
    "ameliorer le cv",
    "améliorer le cv",
    "personnalise le cv",
    "mets a jour le cv",
    "met a jour le cv",
    "ajoute des competences",
    "ajouter des competences",
)


def _is_action_actionable(action: str) -> bool:
    text = _fold_text(action or "").strip()
    if len(text) < 30:
        return False
    if not any(
        marker in text
        for marker in (
            "section",
            "titre",
            "resume",
            "experience",
            "competence",
            "formation",
            "projet",
            "certification",
            "langue",
            "preuve",
            "linkedin",
        )
    ):
        return False
    if any(pattern in text for pattern in _GENERIC_ACTION_PATTERNS):
        return False
    return True


def _parse_json_blob(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(raw.strip())
    except Exception:
        first = raw.find("{")
        last = raw.rfind("}")
        if first >= 0 and last > first:
            try:
                return json.loads(raw[first : last + 1].strip())
            except Exception:
                return None
        return None


def _resolve_job(
    item: dict,
    *,
    jobs_by_id: dict[str, RecommendedJobPreview],
    jobs_by_url: dict[str, RecommendedJobPreview],
    jobs_by_title: dict[str, RecommendedJobPreview],
) -> RecommendedJobPreview | None:
    job_id = str(item.get("job_id") or item.get("jobId") or "").strip()
    title = str(item.get("title") or "").strip()
    url = _canonicalize_url(item.get("url"))
    if job_id and job_id in jobs_by_id:
        return jobs_by_id[job_id]
    if url and url in jobs_by_url:
        return jobs_by_url[url]
    if title:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", _fold_text(title)).strip()
        matched = jobs_by_title.get(normalized_title)
        if matched is not None:
            return matched
        if normalized_title:
            for key, candidate in jobs_by_title.items():
                if normalized_title in key or key in normalized_title:
                    return candidate
    return None


def _collect_allowed_skills(cv_analysis: CVAnalysisResult, job: RecommendedJobPreview) -> set[str]:
    allowed = {_normalize_skill_name(skill) for skill in (cv_analysis.skills or [])}
    job_skills = extract_skills_from_text(" ".join([str(job.title or ""), str(job.summary or "")]))
    for skill in job_skills:
        normalized = _normalize_skill_name(skill)
        if normalized:
            allowed.add(normalized)
    return allowed


def _is_playbook_skill_safe(
    *,
    cv_analysis: CVAnalysisResult,
    job: RecommendedJobPreview,
    target_title: str,
    target_summary: str,
    experience_bullets: list[str],
) -> bool:
    allowed_skills = _collect_allowed_skills(cv_analysis, job)
    if not allowed_skills:
        return True
    proposed_text = " ".join([target_title, target_summary, *experience_bullets]).strip()
    proposed_skills = extract_skills_from_text(proposed_text)
    for skill in proposed_skills:
        normalized = _normalize_skill_name(skill)
        if normalized and normalized not in allowed_skills:
            return False
    return True


def _coerce_assistant_structured(
    raw_payload: object,
    *,
    jobs: list[RecommendedJobPreview],
    cv_analysis: CVAnalysisResult,
    expected_mode: str,
    output_language: str = "fr",
) -> dict | None:
    if isinstance(raw_payload, str):
        payload = _parse_json_blob(raw_payload)
    elif isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        payload = None
    if not isinstance(payload, dict):
        return None
    return _parse_assistant_structured(
        payload,
        jobs=jobs,
        cv_analysis=cv_analysis,
        expected_mode=expected_mode,
        output_language=output_language,
    )


def _parse_assistant_structured(
    payload: dict,
    *,
    jobs: list[RecommendedJobPreview],
    cv_analysis: CVAnalysisResult,
    expected_mode: str,
    output_language: str = "fr",
) -> dict | None:
    profile_summary = str(payload.get("profile_summary") or payload.get("profileSummary") or "").strip()
    strengths = [str(x).strip() for x in (payload.get("strengths") or []) if str(x).strip()]
    gaps = [str(x).strip() for x in (payload.get("gaps") or []) if str(x).strip()]
    actions = [str(x).strip() for x in (payload.get("actions") or []) if str(x).strip()]
    actions = [item for item in actions if _is_action_actionable(item)]
    reason_if_no_match = str(payload.get("reason_if_no_match") or payload.get("reasonIfNoMatch") or "").strip()
    score_explanation = str(payload.get("score_explanation") or payload.get("scoreExplanation") or "").strip()
    raw_mode = str(payload.get("mode") or "").strip().lower()
    mode = expected_mode if expected_mode in {"match", "no_match"} else "no_match"
    if raw_mode in {"match", "no_match"} and raw_mode == expected_mode:
        mode = raw_mode

    if len(profile_summary) < 20:
        profile_summary = _default_profile_summary(cv_analysis)
    if len(strengths) < 2:
        strengths = (strengths + _default_strengths(cv_analysis))[:4]
    if len(gaps) < 2:
        gaps = (gaps + _default_gaps(cv_analysis, jobs))[:4]
    if len(actions) < 2:
        actions = (actions + _default_actions(cv_analysis, jobs))[:5]

    jobs_by_id = {str(job.id): job for job in jobs if str(job.id)}
    jobs_by_url = {_canonicalize_url(job.source_url): job for job in jobs if job.source_url}
    jobs_by_title = {re.sub(r"[^a-z0-9]+", " ", _fold_text(job.title)).strip(): job for job in jobs if job.title}

    recommended_jobs: list[dict[str, str]] = []
    raw_recommended = payload.get("recommended_jobs")
    if not isinstance(raw_recommended, list):
        raw_recommended = payload.get("recommendedJobs")
    if not isinstance(raw_recommended, list):
        raw_recommended = []

    if mode == "match":
        for item in raw_recommended:
            if not isinstance(item, dict):
                continue
            why = str(item.get("why") or "").strip()
            cv_improvement = str(item.get("cv_improvement") or item.get("cvImprovement") or "").strip()
            if len(why) < 10 or len(cv_improvement) < 10:
                continue
            matched_job = _resolve_job(item, jobs_by_id=jobs_by_id, jobs_by_url=jobs_by_url, jobs_by_title=jobs_by_title)
            if matched_job is None:
                continue
            recommended_jobs.append(
                {
                    "job_id": matched_job.id,
                    "title": matched_job.title,
                    "why": why,
                    "url": _canonicalize_url(matched_job.source_url),
                    "cv_improvement": cv_improvement,
                }
            )
            if len(recommended_jobs) >= 3:
                break

        if not recommended_jobs:
            for job in jobs[:3]:
                recommended_jobs.append(
                    {
                        "job_id": job.id,
                        "title": job.title,
                        "why": _fallback_job_why(cv_analysis, job),
                        "url": _canonicalize_url(job.source_url),
                        "cv_improvement": _suggest_cv_improvement_for_job(cv_analysis, job),
                    }
                )
            if not recommended_jobs:
                return None
        reason_if_no_match = ""
    else:
        recommended_jobs = []
        if not reason_if_no_match:
            reason_if_no_match = _no_match_reason("no_meaningful_jobs")

    # Parse offer playbooks with strict anti-invention validation.
    offer_playbooks: list[dict[str, object]] = []
    raw_playbooks = payload.get("offer_playbooks")
    if not isinstance(raw_playbooks, list):
        raw_playbooks = payload.get("offerPlaybooks")
    if not isinstance(raw_playbooks, list):
        raw_playbooks = []

    if mode == "match":
        for item in raw_playbooks:
            if not isinstance(item, dict):
                continue
            matched_job = _resolve_job(item, jobs_by_id=jobs_by_id, jobs_by_url=jobs_by_url, jobs_by_title=jobs_by_title)
            if matched_job is None:
                continue

            rewrite = item.get("rewrite")
            rewrite = rewrite if isinstance(rewrite, dict) else {}
            target_title = str(rewrite.get("target_title") or rewrite.get("targetTitle") or "").strip()
            target_summary = str(rewrite.get("target_summary") or rewrite.get("targetSummary") or "").strip()
            experience_bullets = [
                str(x).strip()
                for x in (rewrite.get("experience_bullets") or rewrite.get("experienceBullets") or [])
                if str(x).strip()
            ]
            why_fit = str(item.get("why_fit") or item.get("whyFit") or "").strip()
            cv_delta = str(item.get("cv_delta") or item.get("cvDelta") or "").strip()
            evidence = [str(x).strip() for x in (item.get("evidence") or []) if str(x).strip()]

            if (
                len(target_title) < 3
                or len(target_summary) < 18
                or len(experience_bullets) < 2
                or len(why_fit) < 10
                or len(cv_delta) < 10
            ):
                continue

            if not _is_playbook_skill_safe(
                cv_analysis=cv_analysis,
                job=matched_job,
                target_title=target_title,
                target_summary=target_summary,
                experience_bullets=experience_bullets,
            ):
                continue

            offer_playbooks.append(
                {
                    "job_id": matched_job.id,
                    "title": matched_job.title,
                    "url": _canonicalize_url(matched_job.source_url),
                    "why_fit": why_fit,
                    "cv_delta": cv_delta,
                    "rewrite": {
                        "target_title": target_title,
                        "target_summary": target_summary,
                        "experience_bullets": experience_bullets[:3],
                    },
                    "evidence": evidence[:3],
                }
            )
            if len(offer_playbooks) >= 3:
                break

        if not offer_playbooks:
            for job in jobs[:3]:
                offer_playbooks.append(
                    _build_default_offer_playbook(
                        cv_analysis=cv_analysis,
                        job=job,
                        language=output_language,
                    )
                )
    else:
        offer_playbooks = []

    if not score_explanation:
        score_explanation = _build_default_score_explanation(
            overall_score=58,
            structure_score=60,
            alignment_score=56,
            evidence_score=52,
            language=output_language,
        )

    return {
        "mode": mode,
        "profile_summary": profile_summary,
        "strengths": strengths[:4],
        "gaps": gaps[:4],
        "recommended_jobs": recommended_jobs,
        "score_explanation": score_explanation,
        "offer_playbooks": offer_playbooks[:3],
        "actions": actions[:5],
        "reason_if_no_match": reason_if_no_match or None,
    }
