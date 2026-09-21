"""Async task endpoints for CV text endpoints."""

from __future__ import annotations

import uuid

from fastapi import BackgroundTasks, HTTPException

from core.task_tracker import get_task_tracker
from .models import CVAnalyzeRequest, TaskResponse, TaskStatusResponse
from .orchestrator import process_cv_text_analysis
from .routes_common import router

__all__ = []


@router.post("/analyze-text-async", response_model=TaskResponse)
async def analyze_cv_text_async(
    request: CVAnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    task_id = f"cv_{uuid.uuid4().hex[:12]}"
    tracker = get_task_tracker()
    tracker.create_task(task_id, "cv_analysis_text")
    background_tasks.add_task(
        process_cv_text_analysis,
        task_id,
        request.cv_text,
        request.file_name,
    )
    return TaskResponse(
        task_id=task_id,
        status="processing",
        message=f"Analyse en cours, suivez progression: GET /api/cv/status/{task_id}",
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_cv_analysis_status(task_id: str) -> TaskStatusResponse:
    tracker = get_task_tracker()
    task_data = tracker.get_task_status(task_id)
    if not task_data:
        raise HTTPException(
            status_code=404,
            detail=f"Tâche '{task_id}' introuvable ou expirée (1h max)",
        )
    return TaskStatusResponse(**task_data)


@router.delete("/{task_id}")
async def delete_cv_task(task_id: str):
    tracker = get_task_tracker()
    tracker.delete_task(task_id)
    return {"deleted": task_id, "message": "Tâche supprimée"}
