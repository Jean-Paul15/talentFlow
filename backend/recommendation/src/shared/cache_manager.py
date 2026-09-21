"""
Gestionnaire de cache Redis pour optimisation des performances.
"""
import logging
import json
from typing import Any, Callable
import pickle

logger = logging.getLogger(__name__)


class CacheManager:
    """Gestionnaire de cache Redis avec fallback gracieux."""
    
    def __init__(self, redis_client, enabled: bool = True):
        self.redis = redis_client
        self.enabled = enabled
    
    def get_cached(
        self,
        key: str,
        compute_fn: Callable,
        ttl: int = 3600,
        serializer: str = 'json'
    ) -> Any:
        """
        Récupère depuis cache ou calcule si absent.
        
        Args:
            key: Clé cache
            compute_fn: Fonction de calcul si MISS
            ttl: Time-to-live en secondes
            serializer: 'json' ou 'pickle'
            
        Returns:
            Valeur (depuis cache ou calculée)
        """
        if not self.enabled:
            return compute_fn()
        
        try:
            cached = self.redis.get(key)
            if cached:
                return self._deserialize(cached, serializer)
        except Exception as e:
            logger.warning(f"Erreur lecture cache: {e}")
        
        result = compute_fn()
        
        try:
            serialized = self._serialize(result, serializer)
            self.redis.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Erreur écriture cache: {e}")
        
        return result
    
    def invalidate(self, pattern: str) -> int:
        """Invalide toutes les clés matchant le pattern."""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Erreur invalidation cache: {e}")
            return 0
    
    def _serialize(self, data: Any, method: str) -> bytes:
        """Sérialise les données selon la méthode choisie."""
        if method == 'json':
            return json.dumps(data).encode('utf-8')
        elif method == 'pickle':
            return pickle.dumps(data)
        else:
            raise ValueError(f"Serializer inconnu: {method}")
    
    def _deserialize(self, data: bytes, method: str) -> Any:
        """Désérialise les données."""
        if method == 'json':
            return json.loads(data.decode('utf-8'))
        elif method == 'pickle':
            return pickle.loads(data)
        else:
            raise ValueError(f"Serializer inconnu: {method}")
