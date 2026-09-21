"""Shared provider helpers for CV text recommendation flows."""

from __future__ import annotations

from core.gemini_llm import sanitize_error_message

__all__ = ["_format_error"]


def _format_error(err: Exception) -> str:
    message = sanitize_error_message(str(err).strip())
    if message:
        return message
    message = sanitize_error_message(err.__class__.__name__)
    if message:
        return message
    return err.__class__.__name__
