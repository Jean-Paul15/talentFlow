"""Document classification route for CV validation."""

from __future__ import annotations

from fastapi import Request

from .budget import _client_ip
from .cv_document_classifier import (
    assess_cv_document_with_optional_llm,
)
from .models import CvDocumentAssessRequest, CvDocumentAssessResponse
from .routes_common import _build_cv_analysis, router


@router.post("/document-assess", response_model=CvDocumentAssessResponse)
async def assess_document_kind(
    request: CvDocumentAssessRequest,
    request_obj: Request,
) -> CvDocumentAssessResponse:
    cv_text = str(request.cv_text or "").strip()
    cv_analysis = _build_cv_analysis(cv_text)
    assessment, used_llm = await assess_cv_document_with_optional_llm(
        cv_text,
        cv_analysis=cv_analysis,
        use_llm=bool(request.use_llm),
        client_ip=_client_ip(request_obj),
    )
    return CvDocumentAssessResponse(
        document_kind=assessment.document_kind,
        cv_confidence=assessment.cv_confidence,
        user_message=assessment.user_message,
        used_llm=used_llm,
    )
