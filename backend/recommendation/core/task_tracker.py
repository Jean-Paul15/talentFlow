# Service de suivi de tâches asynchrones
# Stocke status/progression dans Redis

import json
from typing import Dict, Optional
from datetime import timedelta

from loguru import logger
from redis import Redis


class TaskStatus:
    """Status possibles d'une tâche."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskTracker:
    """
    Gestionnaire de suivi de tâches asynchrones.
    
    Utilise Redis pour stocker status/progression.
    Permet au frontend de poll l'état d'une tâche.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = timedelta(hours=1)  # Expiration auto après 1h
    
    def create_task(self, task_id: str, task_type: str, user_id: Optional[str] = None) -> None:
        """
        Crée une nouvelle tâche.
        
        Args:
            task_id: ID unique de la tâche
            task_type: Type (upload_cv, analyze_match, improve_cv)
            user_id: ID utilisateur (optionnel)
        """
        data = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "step": "Initialisation...",
            "user_id": user_id,
            "result": None,
            "error": None,
        }
        
        key = f"task:{task_id}"
        self.redis.setex(key, self.ttl, json.dumps(data))
        logger.info(f"Tâche créée: {task_id} ({task_type})")
    
    def update_progress(
        self,
        task_id: str,
        progress: int,
        step: str,
        status: str = TaskStatus.PROCESSING
    ) -> None:
        """
        Met à jour la progression d'une tâche.
        
        Args:
            task_id: ID de la tâche
            progress: Progression (0-100)
            step: Description étape en cours
            status: Status (default: processing)
        """
        key = f"task:{task_id}"
        data_str = self.redis.get(key)
        
        if not data_str:
            logger.warning(f"Tâche introuvable: {task_id}")
            return
        
        data = json.loads(data_str)
        data["status"] = status
        data["progress"] = progress
        data["step"] = step
        
        self.redis.setex(key, self.ttl, json.dumps(data))
        logger.debug(f"Tâche {task_id}: {progress}% - {step}")
    
    def complete_task(self, task_id: str, result: Dict) -> None:
        """
        Marque une tâche comme terminée avec succès.
        
        Args:
            task_id: ID de la tâche
            result: Résultat final (dict)
        """
        key = f"task:{task_id}"
        data_str = self.redis.get(key)
        
        if not data_str:
            logger.warning(f"Tâche introuvable: {task_id}")
            return
        
        data = json.loads(data_str)
        data["status"] = TaskStatus.COMPLETED
        data["progress"] = 100
        data["step"] = "Terminé"
        data["result"] = result
        
        # Expiration prolongée pour résultats
        self.redis.setex(key, timedelta(hours=24), json.dumps(data))
        logger.info(f"Tâche terminée: {task_id}")
    
    def fail_task(self, task_id: str, error_message: str) -> None:
        """
        Marque une tâche comme échouée.
        
        Args:
            task_id: ID de la tâche
            error_message: Message d'erreur
        """
        key = f"task:{task_id}"
        data_str = self.redis.get(key)
        
        if not data_str:
            logger.warning(f"Tâche introuvable: {task_id}")
            return
        
        data = json.loads(data_str)
        data["status"] = TaskStatus.FAILED
        data["step"] = "Échec"
        data["error"] = error_message
        
        self.redis.setex(key, timedelta(hours=24), json.dumps(data))
        logger.error(f"Tâche échouée: {task_id} - {error_message}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Récupère le status complet d'une tâche.
        
        Args:
            task_id: ID de la tâche
        
        Returns:
            Dict avec status, progress, step, result, error
            None si tâche introuvable
        """
        key = f"task:{task_id}"
        data_str = self.redis.get(key)
        
        if not data_str:
            return None
        
        return json.loads(data_str)
    
    def delete_task(self, task_id: str) -> None:
        """
        Supprime une tâche (cleanup).
        
        Args:
            task_id: ID de la tâche
        """
        key = f"task:{task_id}"
        self.redis.delete(key)
        logger.debug(f"Tâche supprimée: {task_id}")


# Instance globale
_task_tracker: Optional[TaskTracker] = None


def init_task_tracker(redis_client: Redis) -> TaskTracker:
    """Initialise le tracker global."""
    global _task_tracker
    _task_tracker = TaskTracker(redis_client)
    return _task_tracker


def get_task_tracker() -> TaskTracker:
    """Récupère le tracker global."""
    if _task_tracker is None:
        raise RuntimeError("TaskTracker non initialisé")
    return _task_tracker
