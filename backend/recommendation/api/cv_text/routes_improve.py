"""Offer-improvement route wrapper for CV text flows."""

from __future__ import annotations

from .models import CVImproveForOfferRequest, CVImproveForOfferResponse
from .routes_common import router
from .routes_offer import _improve_cv_for_offer_core

__all__ = []


@router.post("/improve-text-for-offer", response_model=CVImproveForOfferResponse)
async def improve_cv_for_offer(request: CVImproveForOfferRequest) -> CVImproveForOfferResponse:
    return await _improve_cv_for_offer_core(request)
