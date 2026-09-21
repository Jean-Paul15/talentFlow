"""Prompt block builders for recommendation assistant generation."""

from __future__ import annotations

from .models import CVAnalysisResult, RecommendedJobPreview
from .text_utils import _canonicalize_url

__all__ = [
    "_build_recommendation_prompt_blocks",
    "_build_recommendation_prompt",
    "_build_recommendation_messages",
    "_build_compact_recommendation_prompt",
]


def _build_recommendation_prompt_blocks(
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    *,
    expected_mode: str,
    decision_reason: str,
    output_language: str = "fr",
    retry_hint: bool = False,
) -> dict[str, str]:
    lines = []
    for idx, job in enumerate(jobs[:5], start=1):
        lines.append(
            f"{idx}. id={job.id} | title={job.title} | company={job.company or 'N/A'} | "
            f"location={job.location or 'N/A'} | country={job.country or 'N/A'} | "
            f"score={job.score if job.score is not None else 'N/A'} | "
            f"url={job.source_url or 'N/A'} | summary={job.summary}"
        )
    jobs_block = "\n".join(lines) if lines else "No meaningful job retained."
    system_block = (
        "You are TalentFlow's final career assistant.\n"
        "Return strict valid JSON only, without markdown.\n"
        "Do not invent jobs, URLs, skills, or evidence.\n"
    )
    context_block = (
        "The search engine has already decided whether meaningful jobs exist.\n"
        "Your role is to produce a reliable, actionable coaching output.\n\n"
        "Expected JSON schema:\n"
        "{"
        "\"mode\":\"match|no_match\","
        "\"profile_summary\":\"string\","
        "\"strengths\":[\"string\"],"
        "\"gaps\":[\"string\"],"
        "\"recommended_jobs\":[{\"job_id\":\"string\",\"title\":\"string\",\"why\":\"string\",\"url\":\"string\",\"cv_improvement\":\"string\"}],"
        "\"score_explanation\":\"string\","
        "\"offer_playbooks\":[{\"job_id\":\"string\",\"title\":\"string\",\"url\":\"string\",\"why_fit\":\"string\",\"cv_delta\":\"string\",\"rewrite\":{\"target_title\":\"string\",\"target_summary\":\"string\",\"experience_bullets\":[\"string\"]},\"evidence\":[\"string\"]}],"
        "\"actions\":[\"string\"],"
        "\"reason_if_no_match\":\"string|null\""
        "}\n\n"
        f"Engine mode: {expected_mode}\n"
        f"Engine reason: {decision_reason}\n\n"
        "Hard constraints:\n"
        "- if mode=no_match, recommended_jobs must be [] and offer_playbooks must be []\n"
        "- if mode=match, recommended_jobs must contain 1 to 3 jobs\n"
        "- if mode=match, offer_playbooks must contain 1 to 3 playbooks\n"
        "- use snake_case fields only\n"
        "- only use the jobs listed below\n"
        "- copy job_id/title/url exactly from allowed jobs\n"
        "- no invented skill; only skills present in CV signals or in allowed jobs\n"
        "- evidence must cite concrete CV evidence snippets\n"
        "- score_explanation must explain current->target score path and concrete actions\n"
        "- profile_summary must be 1 to 2 sentences\n"
        "- strengths/gaps/actions must be short and concrete\n"
        "- actions must reference explicit CV sections (Titre, Résumé, Expériences, Compétences, Formation, Projets/Certifications, Langues, Centres d'intérêt)\n"
        "- each action must contain: what to change, where to change it, and expected impact\n"
        "- rewrite.target_summary must reuse CV facts only (no fabricated tools, missions, or years)\n"
        "- experience_bullets must be actionable rewrite bullets, each with measurable output when possible\n"
        f"- output language must be: {output_language}\n"
        "- reason_if_no_match must be null in mode=match\n\n"
    )
    payload_block = (
        f"CV analyzed:\n- skills: {', '.join(cv_analysis.skills) or 'N/A'}\n"
        f"- experience_years: {cv_analysis.experience_years}\n"
        f"- education_level: {cv_analysis.education_level}\n"
        f"- preview: {cv_analysis.raw_text_preview}\n\n"
        f"Allowed jobs:\n{jobs_block}\n"
    )
    repair_hint = (
        "IMPORTANT: previous answer failed validation. Return strict JSON only, compliant with schema."
        if retry_hint
        else ""
    )
    return {"system": system_block, "context": context_block, "payload": payload_block, "repair_hint": repair_hint}


def _build_recommendation_prompt(
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    *,
    expected_mode: str,
    decision_reason: str,
    output_language: str = "fr",
    retry_hint: bool = False,
) -> str:
    blocks = _build_recommendation_prompt_blocks(
        cv_analysis,
        jobs,
        expected_mode=expected_mode,
        decision_reason=decision_reason,
        output_language=output_language,
        retry_hint=retry_hint,
    )
    prefix = f"{blocks['repair_hint']}\n\n" if blocks["repair_hint"] else ""
    return prefix + blocks["system"] + "\n" + blocks["context"] + "\n" + blocks["payload"]


def _build_recommendation_messages(
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    *,
    expected_mode: str,
    decision_reason: str,
    output_language: str = "fr",
    retry_hint: bool = False,
) -> list[dict[str, str]]:
    blocks = _build_recommendation_prompt_blocks(
        cv_analysis,
        jobs,
        expected_mode=expected_mode,
        decision_reason=decision_reason,
        output_language=output_language,
        retry_hint=retry_hint,
    )
    user_content = ((f"{blocks['repair_hint']}\n\n" if blocks["repair_hint"] else "") + blocks["context"] + "\n" + blocks["payload"])
    return [{"role": "system", "content": blocks["system"]}, {"role": "user", "content": user_content}]


def _build_compact_recommendation_prompt(
    cv_analysis: CVAnalysisResult,
    jobs: list[RecommendedJobPreview],
    *,
    expected_mode: str,
    decision_reason: str,
    output_language: str = "fr",
) -> str:
    shortlist = jobs[:2]
    jobs_block = "\n".join(
        [
            f"- job_id={job.id} | title={job.title} | url={_canonicalize_url(job.source_url)} | score={float(job.score or 0.0):.3f}"
            for job in shortlist
        ]
    )
    return (
        "Return strict valid JSON only, without markdown.\n"
        "{"
        "\"mode\":\"match|no_match\","
        "\"profile_summary\":\"...\","
        "\"strengths\":[\"...\"],"
        "\"gaps\":[\"...\"],"
        "\"recommended_jobs\":[{\"job_id\":\"...\",\"title\":\"...\",\"why\":\"...\",\"url\":\"...\",\"cv_improvement\":\"...\"}],"
        "\"score_explanation\":\"...\","
        "\"offer_playbooks\":[{\"job_id\":\"...\",\"title\":\"...\",\"url\":\"...\",\"why_fit\":\"...\",\"cv_delta\":\"...\",\"rewrite\":{\"target_title\":\"...\",\"target_summary\":\"...\",\"experience_bullets\":[\"...\"]},\"evidence\":[\"...\"]}],"
        "\"actions\":[\"...\"],"
        "\"reason_if_no_match\":\"... or null\""
        "}\n\n"
        f"Expected mode: {expected_mode}. Engine reason: {decision_reason}.\n"
        f"Constraints: max 2 jobs, no invention, exact job_id/title/url, output language={output_language}.\n"
        f"CV skills: {', '.join(cv_analysis.skills[:8]) or 'N/A'}\n"
        f"Experience: {cv_analysis.experience_years}\n"
        f"Education: {cv_analysis.education_level or 'N/A'}\n"
        f"Jobs:\n{jobs_block}\n"
    )
