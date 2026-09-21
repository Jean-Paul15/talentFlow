# Health Check Endpoint - Monitoring production
from fastapi import APIRouter, Response, status
from typing import Dict, List
import logging
import asyncio
from datetime import datetime
import os

logger = logging.getLogger(__name__)

health_router = APIRouter(prefix="/health", tags=["Health"])


async def check_redis() -> Dict:
    """Vérifie connexion Redis"""
    try:
        from ..core.redis_state_manager import redis_state_manager
        await redis_state_manager.initialize()
        await redis_state_manager._redis.ping()
        return {
            "status": "healthy",
            "latency_ms": 1
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_llm() -> Dict:
    """Vérifie disponibilité LLM"""
    try:
        from ..core.llm_factory_base import LLMFactoryBase
        llm = LLMFactoryBase.get()
        provider = LLMFactoryBase.get_provider()
        
        start = datetime.now()
        await llm.ainvoke("Test")
        latency = (datetime.now() - start).total_seconds() * 1000
        
        return {
            "status": "healthy",
            "provider": provider.value,
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_circuit_breaker() -> Dict:
    """Vérifie état circuit breaker"""
    from ..core.retry_logic import circuit_breaker
    return {
        "status": "healthy" if circuit_breaker.can_attempt() else "degraded",
        "state": circuit_breaker.state.value,
        "failure_count": circuit_breaker.failure_count
    }


@health_router.get("/live")
async def liveness_check():
    """Liveness probe (Kubernetes)"""
    return {"status": "alive"}


@health_router.get("/ready")
async def readiness_check(response: Response):
    """Readiness probe (Kubernetes)
    
    Vérifie que tous les services dépendants sont OK
    """
    checks = {
        "redis": await check_redis(),
        "llm": await check_llm(),
        "circuit_breaker": await check_circuit_breaker()
    }
    
    all_healthy = all(
        check["status"] in ["healthy", "degraded"]
        for check in checks.values()
    )
    
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }


@health_router.get("/")
async def health_check(response: Response):
    """Health check complet
    
    Retourne 200 si OK, 503 si problème critique
    """
    checks = await readiness_check(response)
    
    app_info = {
        "name": "TalentFlow Backend",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    return {
        **checks,
        "app": app_info
    }
