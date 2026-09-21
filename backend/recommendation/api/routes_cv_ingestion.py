from __future__ import annotations

import os

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from services.ocr_pdf_service import extract_pdf_text_with_ocr

router = APIRouter(prefix="/cv-ingestion", tags=["cv-ingestion"])


class OcrPdfResponse(BaseModel):
    strategy: str
    text: str
    extracted_chars: int
    pages_processed: int
    total_pages: int
    ocr_used: bool


def _require_internal_token(x_internal_token: str | None) -> None:
    expected = str(os.getenv("CV_INGESTION_INTERNAL_TOKEN", "")).strip()
    if not expected:
        return
    provided = str(x_internal_token or "").strip()
    if provided != expected:
        raise HTTPException(401, "Unauthorized internal ingestion call")


@router.post("/ocr-pdf", response_model=OcrPdfResponse)
async def ocr_pdf_extract(
    file: UploadFile = File(...),
    max_pages: int = Query(default=10, ge=1, le=30),
    languages: str = Query(default="fra+eng"),
    x_internal_token: str | None = Header(default=None),
) -> OcrPdfResponse:
    _require_internal_token(x_internal_token)
    mime = str(file.content_type or "").lower()
    name = str(file.filename or "").lower()
    if "pdf" not in mime and not name.endswith(".pdf"):
        raise HTTPException(400, "Le fichier doit etre un PDF")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Fichier vide")

    try:
        result = extract_pdf_text_with_ocr(
            file_bytes,
            languages=languages,
            max_pages=max_pages,
        )
    except Exception as err:
        raise HTTPException(422, f"OCR echec: {err}")

    return OcrPdfResponse(
        strategy="ocr_fallback",
        text=result.text,
        extracted_chars=len(result.text),
        pages_processed=result.pages_processed,
        total_pages=result.total_pages,
        ocr_used=True,
    )
