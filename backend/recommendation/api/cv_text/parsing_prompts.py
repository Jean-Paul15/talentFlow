"""Compatibility facade for prompt builders and response mode selection."""

from __future__ import annotations

from .parsing_prompt_blocks import (
    _build_compact_recommendation_prompt,
    _build_recommendation_messages,
    _build_recommendation_prompt,
    _build_recommendation_prompt_blocks,
)
from .parsing_response_mode import _recommendation_response_mode

__all__ = [
    "_build_recommendation_prompt_blocks",
    "_build_recommendation_prompt",
    "_build_recommendation_messages",
    "_build_compact_recommendation_prompt",
    "_recommendation_response_mode",
]
