"""Runtime debug endpoint for CV text recommendation flows."""

from __future__ import annotations

from fastapi import HTTPException

from .budget import _env_bool, get_llm_runtime_state
from .routes_common import router

__all__ = []


@router.get("/llm-runtime")
async def get_llm_runtime():
    if not _env_bool("DEBUG", False):
        raise HTTPException(404, "Not Found")
    return get_llm_runtime_state()
