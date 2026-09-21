"""
Logger sécurité centralisé - Audit trail complet.
Logs tous les événements de sécurité (auth, access, failures).
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import Request
import hashlib


class SecurityLogger:
    """Logger centralisé pour événements de sécurité."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"security.{service_name}")
        self.logger.setLevel(logging.INFO)
        
        # Handler fichier JSON
        handler = logging.FileHandler(f"/var/log/talentflow/security_{service_name}.log")
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ):
        """
        Log un événement de sécurité.
        
        Args:
            event_type: Type d'événement (auth_login, auth_failure, access_denied, etc)
            user_id: ID de l'utilisateur
            ip_address: Adresse IP
            details: Détails supplémentaires
            success: Succès ou échec
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
            "details": details or {},
        }
        
        # Log en JSON (facilite parsing)
        self.logger.info(json.dumps(event))
        
        # Si échec, log aussi en WARNING
        if not success:
            self.logger.warning(f"SECURITY_FAILURE: {event_type} - {user_id} - {ip_address}")
    
    def log_auth_success(self, user_id: str, ip_address: str, method: str = "jwt"):
        """Log authentification réussie."""
        self.log_event(
            event_type="auth_success",
            user_id=user_id,
            ip_address=ip_address,
            details={"method": method},
            success=True,
        )
    
    def log_auth_failure(self, username: str, ip_address: str, reason: str):
        """Log échec authentification (tentative de connexion)."""
        self.log_event(
            event_type="auth_failure",
            user_id=username,  # username (pas encore authentifié)
            ip_address=ip_address,
            details={"reason": reason},
            success=False,
        )
    
    def log_access_denied(self, user_id: str, ip_address: str, resource: str, reason: str):
        """Log accès refusé (authorization)."""
        self.log_event(
            event_type="access_denied",
            user_id=user_id,
            ip_address=ip_address,
            details={"resource": resource, "reason": reason},
            success=False,
        )
    
    def log_suspicious_activity(self, user_id: Optional[str], ip_address: str, activity: str, details: dict):
        """Log activité suspecte."""
        self.log_event(
            event_type="suspicious_activity",
            user_id=user_id,
            ip_address=ip_address,
            details={"activity": activity, **details},
            success=False,
        )
    
    def log_data_access(self, user_id: str, ip_address: str, resource_type: str, resource_id: str):
        """Log accès à des données sensibles."""
        self.log_event(
            event_type="data_access",
            user_id=user_id,
            ip_address=ip_address,
            details={"resource_type": resource_type, "resource_id": resource_id},
            success=True,
        )
    
    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str, limit: str):
        """Log dépassement de rate limit."""
        self.log_event(
            event_type="rate_limit_exceeded",
            user_id=None,
            ip_address=ip_address,
            details={"endpoint": endpoint, "limit": limit},
            success=False,
        )


def get_client_ip(request: Request) -> str:
    """Extrait l'IP réelle du client (supporte proxy)."""
    # Si derrière proxy (X-Forwarded-For)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Si X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Sinon IP directe
    return request.client.host if request.client else "unknown"


def audit_trail(event_type: str):
    """
    Décorateur pour logger automatiquement les endpoints.
    
    Usage:
        @audit_trail("cv_analysis")
        async def analyze_cv(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraire request et user si disponibles
            request = kwargs.get("request") or (args[0] if args and isinstance(args[0], Request) else None)
            
            # Logger AVANT exécution
            if request:
                ip = get_client_ip(request)
                logger = SecurityLogger(func.__module__)
                logger.log_event(
                    event_type=f"{event_type}_start",
                    ip_address=ip,
                    details={"endpoint": func.__name__},
                )
            
            # Exécuter fonction
            try:
                result = await func(*args, **kwargs)
                
                # Logger SUCCÈS
                if request:
                    logger.log_event(
                        event_type=f"{event_type}_success",
                        ip_address=ip,
                        details={"endpoint": func.__name__},
                        success=True,
                    )
                
                return result
            
            except Exception as e:
                # Logger ÉCHEC
                if request:
                    logger.log_event(
                        event_type=f"{event_type}_failure",
                        ip_address=ip,
                        details={"endpoint": func.__name__, "error": str(e)},
                        success=False,
                    )
                raise
        
        return wrapper
    return decorator


# Instance globale pour chaque service
def get_security_logger(service_name: str) -> SecurityLogger:
    """Récupère logger sécurité pour un service."""
    return SecurityLogger(service_name)


# Configuration logging sécurité
def configure_security_logging():
    """Configure le système de logging sécurité."""
    import os
    
    # Créer dossier logs si nécessaire
    log_dir = "/var/log/talentflow"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuration rotation logs (à implémenter si besoin)
    # Via logrotate ou RotatingFileHandler
