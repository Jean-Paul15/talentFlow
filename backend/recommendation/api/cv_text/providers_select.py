"""Provider selection and orchestration helpers for CV text recommendation flows."""

from __future__ import annotations

import os

try:  # pragma: no cover
    from core.metrics import llm_fallback_total, llm_reasoner_downgrade_total
except Exception:  # pragma: no cover
    llm_fallback_total = None
    llm_reasoner_downgrade_total = None

from .budget import _deepseek_reasoner_allowed_by_share, _env_float

__all__ = [
    "_resolve_explicit_provider",
    "_resolve_provider_explicit_model",
    "_gemini_candidate_models",
    "_recommendation_complexity_score",
    "_pick_deepseek_model",
]


def _resolve_explicit_provider(explicit_model: str | None) -> str | None:
    """
    Déduit un provider explicitement ciblé.
    Supporte:
    - llm_model="gemini:gemini-2.5-flash"
    - llm_model="deepseek:deepseek-chat"
    - llm_model="gemini-2.5-flash"
    - llm_model="deepseek-chat"
    """
    raw = str(explicit_model or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if ":" in lowered:
        prefix, _ = lowered.split(":", 1)
        if prefix in {"gemini", "deepseek"}:
            return prefix
        return None
    if lowered.startswith("gemini"):
        return "gemini"
    if lowered.startswith("deepseek"):
        return "deepseek"
    return None


def _resolve_provider_explicit_model(explicit_model: str | None, *, provider: str) -> str | None:
    """
    Résout explicitement un modèle Gemini demandé par le client.
    Supporte:
    - llm_model="gemini:gemini-2.5-flash"
    - llm_model="gemini-2.5-flash"
    """
    raw = str(explicit_model or "").strip()
    if not raw:
        return None
    if ":" in raw:
        prefix, value = raw.split(":", 1)
        if prefix.strip().lower() == provider:
            value = value.strip()
            return value or None
        return None

    lowered = raw.lower()
    if provider == "gemini":
        return raw if lowered.startswith("gemini") else None
    if provider == "deepseek":
        return raw if lowered.startswith("deepseek") else None
    return None


def _gemini_candidate_models(primary: str | None) -> list[str]:
    """
    Liste ordonnée des modèles Gemini à tenter.
    """
    models: list[str] = []
    if primary:
        models.append(str(primary).strip())

    env_priority = str(os.getenv("GEMINI_MODEL_PRIORITY", "")).strip()
    if env_priority:
        models.extend([m.strip() for m in env_priority.split(",") if m.strip()])

    models.extend(
        [
            str(os.getenv("GEMINI_MODEL") or "").strip(),
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
        ]
    )

    out: list[str] = []
    seen: set[str] = set()
    for m in models:
        if not m:
            continue
        key = m.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _recommendation_complexity_score(
    *,
    prompt: str,
    expected_mode: str | None,
    attempt: int,
) -> float:
    score = 0.0
    prompt_len = len(prompt or "")
    if prompt_len > 1800:
        score += 0.5
    if prompt_len > 2600:
        score += 0.5
    if (expected_mode or "") == "no_match":
        score += 0.2
    if attempt > 0:
        score += 0.5
    return score


def _pick_deepseek_model(
    *,
    prompt: str,
    explicit_model: str | None,
    expected_mode: str | None,
    attempt: int,
    budget_state: dict[str, float],
) -> str:
    explicit = _resolve_provider_explicit_model(explicit_model, provider="deepseek")
    if explicit:
        return explicit
    chat_model = str(os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip() or "deepseek-chat"
    reasoner_model = str(os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")).strip() or "deepseek-reasoner"
    threshold = max(0.1, _env_float("DEEPSEEK_REASONER_COMPLEXITY_THRESHOLD", 1.0))
    if _recommendation_complexity_score(prompt=prompt, expected_mode=expected_mode, attempt=attempt) < threshold:
        return chat_model
    if not _deepseek_reasoner_allowed_by_share(budget_state):
        if llm_reasoner_downgrade_total is not None:
            llm_reasoner_downgrade_total.labels(reason="share_cap").inc()
        return chat_model
    if budget_state.get("token_ratio", 0.0) >= 0.85 or budget_state.get("cost_ratio", 0.0) >= 0.85:
        if llm_reasoner_downgrade_total is not None:
            llm_reasoner_downgrade_total.labels(reason="budget_guard").inc()
        return chat_model
    return reasoner_model
