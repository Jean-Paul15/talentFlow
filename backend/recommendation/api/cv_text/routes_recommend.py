"""Recommendation route wrapper for CV text flows."""

from __future__ import annotations

from fastapi import Request

from .models import CVRecommendTextRequest, CVRecommendTextResponse
from .routes_common import router
from .routes_jobs import _recommend_from_cv_text_core

__all__ = []


@router.post("/recommend-text", response_model=CVRecommendTextResponse)
async def recommend_from_cv_text(
    request: CVRecommendTextRequest,
    request_obj: Request,
) -> CVRecommendTextResponse:
    return await _recommend_from_cv_text_core(request, request_obj)
