from __future__ import annotations

from fastapi import HTTPException
from loguru import logger


def build_filters(location: str | None, contract_type: str | None, skills: list[str] | None) -> dict:
    filters: dict = {}
    if location:
        filters['location'] = location
    if contract_type:
        filters['contract_type'] = contract_type
    if skills:
        filters['skills'] = skills
    return filters


def as_http_500(err: Exception, context: str) -> HTTPException:
    logger.error(f"Erreur {context}: {err}")
    return HTTPException(status_code=500, detail=str(err))
