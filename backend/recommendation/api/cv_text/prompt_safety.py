"""Prompt-safety helpers for CV text used in LLM prompts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .text_utils import _fold_text

__all__ = [
    "PromptSafetyAssessment",
    "assess_prompt_injection_risk",
    "detect_cv_language",
]


@dataclass(slots=True)
class PromptSafetyAssessment:
    risk_score: float
    blocked: bool
    sanitized_text: str
    matched_rules: list[str]


_RULES: tuple[tuple[str, str, float], ...] = (
    ("ignore_instructions", r"\b(ignore|disregard|bypass)\b.{0,40}\b(previous|prior|above)\b", 0.34),
    ("system_prompt", r"\b(system prompt|developer message|hidden prompt|jailbreak)\b", 0.36),
    ("role_override", r"\b(you are chatgpt|act as|pretend to be|role: system)\b", 0.26),
    ("tool_or_api_call", r"\b(tool call|function call|jsonrpc|mcp-session-id)\b", 0.26),
    ("exfiltration", r"\b(show|reveal|leak|print)\b.{0,48}\b(prompt|secret|key|token)\b", 0.34),
    ("instruction_block", r"(###\s*instruction|<\s*instruction\s*>|BEGIN PROMPT|END PROMPT)", 0.22),
)

_DROP_LINE_HINTS: tuple[str, ...] = (
    "ignore previous",
    "ignore above",
    "disregard previous",
    "system prompt",
    "developer message",
    "jailbreak",
    "jsonrpc",
    "tool call",
    "function call",
    "print the prompt",
    "reveal the prompt",
    "show me the prompt",
)


def _env_float(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except Exception:
        return default
    return max(0.0, min(1.0, value))


def _sanitize_cv_text(text: str) -> str:
    lines = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = _fold_text(line)
        if any(token in lowered for token in _DROP_LINE_HINTS):
            continue
        if lowered.startswith(("assistant:", "system:", "developer:", "user:")):
            continue
        if "```" in line:
            continue
        lines.append(line)
    sanitized = "\n".join(lines).strip()
    if not sanitized:
        return str(text or "").strip()
    return sanitized


def assess_prompt_injection_risk(cv_text: str) -> PromptSafetyAssessment:
    text = str(cv_text or "").replace("\x00", " ").strip()
    folded = _fold_text(text)
    matched: list[str] = []
    risk = 0.0
    for label, pattern, weight in _RULES:
        if re.search(pattern, folded):
            matched.append(label)
            risk += weight
    if "```" in text:
        risk += 0.10
    word_count = len([token for token in re.split(r"\s+", text) if token])
    if word_count > 0:
        risk += min(0.22, (len(matched) / max(word_count, 1)) * 40)
    risk = max(0.0, min(1.0, risk))

    sanitize_threshold = _env_float("CV_PROMPT_SANITIZE_THRESHOLD", 0.12)
    block_threshold = _env_float("CV_PROMPT_BLOCK_THRESHOLD", 0.68)
    sanitized = _sanitize_cv_text(text) if risk >= sanitize_threshold else text
    blocked = risk >= block_threshold and len(matched) > 0

    return PromptSafetyAssessment(
        risk_score=round(risk, 3),
        blocked=blocked,
        sanitized_text=sanitized,
        matched_rules=matched,
    )


def detect_cv_language(cv_text: str) -> str:
    text = _fold_text(cv_text)
    if not text:
        return "fr"
    fr_hits = sum(
        1
        for token in (
            "experience",
            "competences",
            "formation",
            "profil",
            "entreprise",
            "mission",
            "stage",
            "candidature",
        )
        if token in text
    )
    en_hits = sum(
        1
        for token in (
            "experience",
            "skills",
            "education",
            "profile",
            "company",
            "internship",
            "resume",
            "application",
        )
        if token in text
    )
    es_hits = sum(
        1
        for token in (
            "experiencia",
            "habilidades",
            "educacion",
            "perfil",
            "empresa",
            "candidatura",
            "curriculum",
        )
        if token in text
    )
    if en_hits >= fr_hits + 2 and en_hits >= es_hits:
        return "en"
    if es_hits >= fr_hits + 2 and es_hits >= en_hits:
        return "es"
    return "fr"
