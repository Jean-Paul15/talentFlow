# Redis State Manager - Persistance robuste
import logging
import json
from typing import Optional, Dict, Callable
from uuid import uuid4
import redis.asyncio as aioredis
from redis.exceptions import RedisError
import os

from .analysis_state import AnalysisState, AnalysisStatus

logger = logging.getLogger(__name__)


class RedisStateManager:
    """State manager avec Redis (scalable + persistent)"""
    
    _instance = None
    _redis: Optional[aioredis.Redis] = None
    _prefix = "analysis:"
    _ttl = 86400  # 24 heures
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Initialise connexion Redis"""
        if self._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            try:
                self._redis = await aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    retry_on_timeout=True
                )
                await self._redis.ping()
                logger.info(f"Redis connecté: {redis_url}")
            except RedisError as e:
                logger.error(f"Redis connexion échouée: {e}")
                raise
    
    async def create_analysis(self, analysis_type: str, user_id: str) -> str:
        """Crée analyse dans Redis"""
        task_id = f"task_{uuid4().hex[:16]}"
        state = AnalysisState(task_id, analysis_type, user_id)
        
        key = f"{self._prefix}{task_id}"
        try:
            await self._redis.setex(
                key,
                self._ttl,
                json.dumps(state.to_dict())
            )
            logger.info(f"Analyse créée: {task_id}")
            return task_id
        except RedisError as e:
            logger.error(f"Erreur création analyse: {e}")
            raise
    
    async def get_state(self, task_id: str) -> Optional[AnalysisState]:
        """Récupère état depuis Redis"""
        key = f"{self._prefix}{task_id}"
        try:
            data = await self._redis.get(key)
            if not data:
                return None
            
            state_dict = json.loads(data)
            return AnalysisState.from_dict(state_dict)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Erreur récupération état: {e}")
            return None
    
    async def update_state(
        self,
        task_id: str,
        status=None,
        step=None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        partial_result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Met à jour état dans Redis"""
        state = await self.get_state(task_id)
        if not state:
            logger.warning(f"Analyse non trouvée: {task_id}")
            return
        
        await state.update(
            status=status,
            step=step,
            progress=progress,
            message=message,
            partial_result=partial_result,
            error=error
        )
        
        key = f"{self._prefix}{task_id}"
        try:
            await self._redis.setex(
                key,
                self._ttl,
                json.dumps(state.to_dict())
            )
        except RedisError as e:
            logger.error(f"Erreur mise à jour état: {e}")
            raise


redis_state_manager = RedisStateManager()
