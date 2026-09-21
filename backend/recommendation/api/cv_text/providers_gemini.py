"""Gemini generation helpers for CV text recommendation flows."""

from __future__ import annotations

from loguru import logger

from core.gemini_llm import GeminiLLM

from .budget import _env_float
from .providers_common import _format_error

__all__ = ["_generate_with_gemini"]


async def _generate_with_gemini(
    prompt: str,
    model: str | None = None,
    structured_schema: dict | None = None,
) -> tuple[str | None, str | None, str | None]:
    try:
        llm = GeminiLLM.from_env(
            model=model,
            temperature=_env_float("LLM_TEMPERATURE", 0.2),
        )
        result = await llm.agenerate(
            prompt,
            response_mime_type=("application/json" if structured_schema else None),
            response_json_schema=structured_schema,
        )
        return result.text, result.model, None
    except Exception as err:
        formatted = _format_error(err)
        logger.warning(f"Gemini indisponible/failure: {formatted}")
        return None, None, formatted
