# LLM Providers - Gemini-only runtime
from __future__ import annotations

from .gemini_llm import GeminiLLM


def create_llm_instance(provider: str, **kwargs):
    normalized = (provider or "gemini").strip().lower()
    if normalized != "gemini":
        raise ValueError(f"Provider non supporte par la politique Gemini-only: {provider}")

    model = kwargs.get("model")
    temperature = kwargs.get("temperature")
    return GeminiLLM.from_env(model=model, temperature=temperature)
