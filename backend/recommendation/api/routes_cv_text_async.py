"""Backward-compatible route shim for the text CV API."""

from api.cv_text.routes import get_llm_runtime_state, router

__all__ = ["router", "get_llm_runtime_state"]
