# Client Redis pour gestion des fingerprints et cache
# Permet de détecter les doublons lors du scraping

import os
import json
import hashlib
from typing import Any, Dict, Optional, Set
import redis
from loguru import logger


class RedisFingerprint:
    """
    Client Redis pour gestion des fingerprints (déduplication).
    Utilise Redis pour stocker les hashs des jobs déjà scrapés.
    """
    
    def __init__(self):
        """Initialise la connexion Redis."""
        redis_url = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        
        try:
            # Parser l'URL Redis
            if redis_url.startswith("redis://"):
                parts = redis_url.replace("redis://", "").split(":")
                host = parts[0] if parts else "localhost"
                port = int(parts[1].split("/")[0]) if len(parts) > 1 else 6379
                db = int(parts[1].split("/")[1]) if "/" in parts[1] else 0
            else:
                host, port, db = "localhost", 6379, 0
            
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Tester la connexion
            self.redis.ping()
            logger.info(f"✓ Redis connecté ({host}:{port})")
            
        except Exception as e:
            logger.error(f"✗ Erreur connexion Redis: {e}")
            self.redis = None
    
    def _compute_fingerprint(self, data: Dict[str, Any]) -> str:
        """Calcule le fingerprint (hash) d'un job."""
        try:
            # Clés importantes pour déduplication
            key_fields = {
                "title": data.get("title", ""),
                "company": data.get("company", ""),
                "link": data.get("link", ""),
            }
            
            json_str = json.dumps(key_fields, sort_keys=True)
            return hashlib.md5(json_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Erreur calcul fingerprint: {e}")
            return None
    
    def exists(self, fingerprint: str) -> bool:
        """Vérifie si un fingerprint existe déjà."""
        return self.exists_prefixed("fingerprint", fingerprint)

    def exists_prefixed(self, prefix: str, key: str) -> bool:
        """Vérifie si une clé préfixée existe."""
        if self.redis is None:
            return False
        try:
            return self.redis.exists(f"{prefix}:{key}") > 0
        except Exception as e:
            logger.error(f"Erreur vérification fingerprint: {e}")
            return False
    
    def add(self, fingerprint: str, data: Dict[str, Any]) -> bool:
        """Ajoute un fingerprint au cache."""
        return self.add_prefixed("fingerprint", fingerprint, data)

    def add_prefixed(
        self,
        prefix: str,
        key: str,
        data: Dict[str, Any],
        *,
        ttl_seconds: int = 86400 * 30,
    ) -> bool:
        """Ajoute une clé préfixée au cache."""
        if self.redis is None:
            return False
        try:
            self.redis.setex(
                f"{prefix}:{key}",
                ttl_seconds,
                json.dumps(data)
            )
            return True
        except Exception as e:
            logger.error(f"Erreur ajout fingerprint: {e}")
            return False
    
    def remove(self, fingerprint: str) -> bool:
        """Supprime un fingerprint."""
        if self.redis is None:
            return False
        try:
            self.redis.delete(f"fingerprint:{fingerprint}")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression fingerprint: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques Redis."""
        if self.redis is None:
            return {"status": "disconnected"}
        
        try:
            info = self.redis.info()
            keys = self.redis.dbsize()
            
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "total_keys": keys,
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.error(f"Erreur stats Redis: {e}")
            return {"status": "error", "message": str(e)}
    
    def clear(self) -> bool:
        """Efface tous les fingerprints."""
        if self.redis is None:
            return False
        try:
            # Utiliser SCAN pour éviter bloquer Redis
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(
                    cursor,
                    match="fingerprint:*",
                    count=100
                )
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"Erreur clear Redis: {e}")
            return False
