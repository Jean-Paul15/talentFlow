"""
Service de cache Redis pour l'analyse CV.
Stocke les résultats d'analyse pour 24h.
"""

import json
from typing import Optional, Dict, Any
from redis import Redis
from datetime import timedelta
from loguru import logger


class CVAnalysisCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = timedelta(hours=24)

    def generate_key(self, cv_id: str, job_id: str) -> str:
        """Génère clé cache format: cv_analysis:{cv_id}:{job_id}"""
        return f"cv_analysis:{cv_id}:{job_id}"

    async def get(self, cv_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Récupère résultat d'analyse du cache."""
        try:
            key = self.generate_key(cv_id, job_id)
            cached = self.redis.get(key)
            
            if cached:
                logger.info(f"Cache HIT: {key}")
                return json.loads(cached)
            
            logger.info(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def set(
        self,
        cv_id: str,
        job_id: str,
        analysis: Dict[str, Any],
    ) -> bool:
        """Stocke résultat d'analyse dans cache."""
        try:
            key = self.generate_key(cv_id, job_id)
            value = json.dumps(analysis)
            
            # Stocke avec TTL 24h
            self.redis.setex(
                key,
                int(self.ttl.total_seconds()),
                value,
            )
            
            logger.info(f"Cache SET: {key} (TTL: 24h)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def delete(self, cv_id: str, job_id: str) -> bool:
        """Supprime résultat du cache."""
        try:
            key = self.generate_key(cv_id, job_id)
            self.redis.delete(key)
            logger.info(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            return False

    async def clear_cv(self, cv_id: str) -> int:
        """Supprime tous les caches pour un CV."""
        try:
            pattern = f"cv_analysis:{cv_id}:*"
            keys = self.redis.keys(pattern)
            
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Cache CLEAR: {deleted} keys for CV {cv_id}")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            return 0

    async def stats(self) -> Dict[str, Any]:
        """Récupère stats du cache."""
        try:
            pattern = "cv_analysis:*"
            keys = self.redis.keys(pattern)
            
            return {
                "cached_analyses": len(keys),
                "keys": [k.decode() if isinstance(k, bytes) else k for k in keys[:10]],
                "redis_memory_bytes": self.redis.info().get("used_memory", 0),
            }
        except Exception as e:
            logger.error(f"Cache STATS error: {e}")
            return {"error": str(e)}
