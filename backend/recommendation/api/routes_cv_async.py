# Routes asynchrones pour upload CV avec tracking

import uuid
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.cv_storage import cv_storage
from core.task_tracker import get_task_tracker, TaskStatus
from services.cv_analyzer import analyze_cv

router = APIRouter(prefix="/cv/async", tags=["cv-async"])


class TaskResponse(BaseModel):
    """Réponse immédiate avec task_id."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Status d'une tâche."""
    task_id: str
    task_type: str
    status: str
    progress: int
    step: str
    result: dict | None = None
    error: str | None = None


async def process_cv_upload(task_id: str, file_path: str, cv_id: str):
    """
    Traite l'upload CV en arrière-plan.
    
    Args:
        task_id: ID de la tâche de tracking
        file_path: Chemin du fichier CV
        cv_id: ID du CV
    """
    tracker = get_task_tracker()
    
    try:
        # Étape 1: Extraction texte
        tracker.update_progress(task_id, 30, "Extraction du texte du CV...")
        
        # Étape 2: Analyse NLP
        tracker.update_progress(task_id, 60, "Analyse des compétences...")
        cv_data = analyze_cv(file_path)
        
        if not cv_data:
            tracker.fail_task(task_id, "Erreur lors de l'analyse du CV")
            cv_storage.cleanup(cv_id)
            return
        
        # Étape 3: Cache résultat
        tracker.update_progress(task_id, 90, "Sauvegarde des résultats...")
        cv_storage.cache_analysis(cv_id, cv_data)
        
        # Étape 4: Terminé
        result = {
            "cv_id": cv_id,
            "skills": cv_data.get("skills", []),
            "experience_years": cv_data.get("experience_years"),
            "education_level": cv_data.get("education_level"),
        }
        tracker.complete_task(task_id, result)
        
    except Exception as e:
        tracker.fail_task(task_id, str(e))
        cv_storage.cleanup(cv_id)


@router.post("/upload", response_model=TaskResponse)
async def upload_cv_async(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> TaskResponse:
    """
    Upload CV de manière asynchrone.
    
    Retourne immédiatement un task_id.
    Le frontend peut ensuite poll /status/{task_id}.
    
    Args:
        file: Fichier CV (PDF, DOCX, TXT)
        background_tasks: FastAPI background tasks
    
    Returns:
        TaskResponse avec task_id pour polling
    """
    # Valider format
    if not file.filename:
        raise HTTPException(400, "Nom de fichier requis")
    
    suffix = file.filename.split(".")[-1].lower()
    if suffix not in ["pdf", "docx", "txt"]:
        raise HTTPException(400, f"Format non supporté: {suffix}")
    
    # Sauvegarder fichier
    cv_id = await cv_storage.save_cv(file)
    file_path = str(cv_storage.get_path(cv_id))
    
    # Créer tâche de tracking
    task_id = f"upload_cv_{uuid.uuid4().hex[:12]}"
    tracker = get_task_tracker()
    tracker.create_task(task_id, "upload_cv")
    
    # Lancer traitement en arrière-plan
    background_tasks.add_task(process_cv_upload, task_id, file_path, cv_id)
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Upload en cours, utilisez GET /status/{task_id} pour suivre la progression"
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_upload_status(task_id: str) -> TaskStatusResponse:
    """
    Récupère le status d'une tâche d'upload.
    
    Le frontend doit appeler ce endpoint toutes les 2s
    pour avoir les updates de progression.
    
    Args:
        task_id: ID de la tâche (retourné par /upload)
    
    Returns:
        TaskStatusResponse avec status, progress, result
    """
    tracker = get_task_tracker()
    task_data = tracker.get_task_status(task_id)
    
    if not task_data:
        raise HTTPException(404, "Tâche introuvable ou expirée")
    
    return TaskStatusResponse(**task_data)


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    Supprime une tâche terminée (cleanup).
    
    Args:
        task_id: ID de la tâche
    
    Returns:
        Confirmation de suppression
    """
    tracker = get_task_tracker()
    tracker.delete_task(task_id)
    return {"deleted": task_id}
