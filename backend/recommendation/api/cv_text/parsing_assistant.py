"""Compatibility facade for structured assistant payload helpers."""

from __future__ import annotations

from .parsing_assistant_defaults import (
    _default_actions,
    _default_gaps,
    _default_profile_summary,
    _default_strengths,
    _recommendation_structured_schema,
)
from .parsing_assistant_structured import (
    _build_fallback_assistant_structured,
    _coerce_assistant_structured,
    _llm_status_from_error,
    _parse_assistant_structured,
    _parse_json_blob,
    _render_assistant_structured,
)

__all__ = [
    "_parse_json_blob",
    "_default_profile_summary",
    "_default_strengths",
    "_default_gaps",
    "_default_actions",
    "_recommendation_structured_schema",
    "_build_fallback_assistant_structured",
    "_coerce_assistant_structured",
    "_parse_assistant_structured",
    "_render_assistant_structured",
    "_llm_status_from_error",
]
