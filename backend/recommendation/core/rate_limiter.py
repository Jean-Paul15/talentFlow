"""
Configuration du Rate Limiting pour la recommandation.
Limite: 100 requêtes par minute par IP/user.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except Exception:  # pragma: no cover - fallback runtime
    class RateLimitExceeded(Exception):
        def __init__(self, detail: str = "rate limit disabled"):
            self.detail = detail

    def get_remote_address(request: Request) -> str:
        return "unknown"

    class Limiter:  # no-op fallback
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator


# Création du limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # 100 requêtes par minute par défaut
)


# Configuration par endpoint (optionnel)
RATE_LIMIT_CONFIG = {
    "analyze_match": "50/minute",      # 50 req/min pour analyze (coûteux)
    "improve_cv": "30/minute",         # 30 req/min pour LLM (très coûteux)
    "search": "200/minute",            # 200 req/min pour search (léger)
    "upload_cv": "20/minute",          # 20 req/min pour uploads
    "health": "1000/minute",           # Pas de limite pour health
}


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Gestionnaire d'exception pour rate limiting."""
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "Trop de requêtes",
            "message": "Vous avez dépassé la limite. Réessayez plus tard.",
            "limit": exc.detail,
        },
    )


def get_rate_limit(endpoint: str) -> str:
    """Récupère limite de rate pour un endpoint."""
    return RATE_LIMIT_CONFIG.get(endpoint, "100/minute")
