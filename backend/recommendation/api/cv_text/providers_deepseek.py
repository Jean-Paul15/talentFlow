"""DeepSeek generation helpers for CV text recommendation flows."""

from __future__ import annotations

from loguru import logger

from core.deepseek_llm import DeepSeekLLM

from .budget import _env_float, _env_int
from .providers_common import _format_error

__all__ = ["_generate_with_deepseek"]


async def _generate_with_deepseek(
    prompt: str,
    model: str | None = None,
    structured_schema: dict | None = None,
    messages: list[dict[str, str]] | None = None,
) -> tuple[str | None, str | None, str | None, dict | None]:
    try:
        llm = DeepSeekLLM.from_env(
            model=model,
            temperature=_env_float("LLM_TEMPERATURE", 0.2),
        )
        is_reasoner = "reasoner" in str(model or "").lower()
        result = await llm.agenerate(
            prompt,
            response_json_schema=structured_schema,
            messages=messages,
            max_output_tokens=(
                _env_int("DEEPSEEK_MAX_OUTPUT_TOKENS_REASONER", 1600)
                if is_reasoner
                else _env_int("DEEPSEEK_MAX_OUTPUT_TOKENS_CHAT", 700)
            ),
        )
        usage = {
            "prompt_tokens": int(result.prompt_tokens or 0),
            "completion_tokens": int(result.completion_tokens or 0),
            "total_tokens": int(result.total_tokens or 0),
            "estimated_cost_usd": float(result.estimated_cost_usd or 0.0),
        }
        return result.text, result.model, None, usage
    except Exception as err:
        formatted = _format_error(err)
        logger.warning(f"DeepSeek indisponible/failure: {formatted}")
        return None, None, formatted, None
