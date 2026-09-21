"""Synchronous analysis endpoint for CV text flows."""

from __future__ import annotations

from .models import CVAnalyzeRequest, CVAnalysisResult
from .cv_document_classifier import ensure_cv_document_or_raise
from .routes_common import _build_cv_analysis, _ensure_cv_text, router

__all__ = []


@router.post("/analyze-text", response_model=CVAnalysisResult)
async def analyze_cv_text_sync(request: CVAnalyzeRequest) -> CVAnalysisResult:
    cv_text = _ensure_cv_text(request.cv_text)
    cv_analysis = _build_cv_analysis(cv_text)
    await ensure_cv_document_or_raise(
        cv_text,
        cv_analysis=cv_analysis,
        use_llm=False,
        client_ip="internal",
    )
    return cv_analysis
