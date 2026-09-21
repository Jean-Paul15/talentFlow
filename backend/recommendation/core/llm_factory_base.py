# LLM Factory - Base Gemini-only
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Optional

from .llm_providers import create_llm_instance

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    GEMINI = "gemini"


class LLMFactoryBase:
    _instance = None
    _provider = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, provider: Optional[str] = None, **kwargs):
        normalized = (provider or os.getenv("LLM_PROVIDER", "gemini")).strip().lower() or "gemini"
        if normalized != "gemini":
            raise ValueError(f"Provider non supporte par la politique Gemini-only: {normalized}")

        logger.info("Initialisation LLM: gemini")
        cls._instance = create_llm_instance("gemini", **kwargs)
        cls._provider = LLMProvider.GEMINI
        cls._config = kwargs
        return cls._instance

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls.initialize()
        return cls._instance

    @classmethod
    def get_provider(cls) -> LLMProvider:
        if cls._provider is None:
            cls.initialize()
        return cls._provider

    @classmethod
    def switch_provider(cls, provider: str, **kwargs):
        normalized = (provider or "").strip().lower()
        if normalized != "gemini":
            raise ValueError("Seul Gemini est supporte")
        cls._instance = None
        cls._provider = None
        cls.initialize(provider="gemini", **kwargs)


class LLMFactory(LLMFactoryBase):
    pass
