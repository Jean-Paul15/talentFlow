"""CV text recommendation routes."""

from .routes_impl import get_llm_runtime_state, router

__all__ = ["router", "get_llm_runtime_state"]
