from __future__ import annotations

import re
from dataclasses import dataclass

import pypdfium2 as pdfium
import pytesseract


@dataclass
class OcrPdfResult:
    text: str
    pages_processed: int
    total_pages: int


def _normalize_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text_with_ocr(
    file_bytes: bytes,
    *,
    languages: str = "fra+eng",
    max_pages: int = 10,
    scale: float = 2.0,
) -> OcrPdfResult:
    if not file_bytes:
        raise RuntimeError("Fichier PDF vide")
    if max_pages <= 0:
        raise RuntimeError("max_pages doit etre > 0")

    doc = pdfium.PdfDocument(file_bytes)
    total_pages = len(doc)
    if total_pages <= 0:
        raise RuntimeError("PDF sans page")

    pages_to_process = min(total_pages, max_pages)
    chunks: list[str] = []

    for idx in range(pages_to_process):
        page = doc[idx]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        text = pytesseract.image_to_string(
            pil_image,
            lang=languages,
            config="--oem 1 --psm 6",
        )
        cleaned = _normalize_text(text)
        if cleaned:
            chunks.append(cleaned)

    merged = _normalize_text("\n\n".join(chunks))
    return OcrPdfResult(
        text=merged,
        pages_processed=pages_to_process,
        total_pages=total_pages,
    )
