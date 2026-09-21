"""FastAPI entrypoint for recommendation service.

Current stable mode is text-based CV analysis (frontend extracts text locally and
sends text to backend). Legacy upload/RAG routes are loaded only if available.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from redis import Redis

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except Exception:  # pragma: no cover
    from core.rate_limiter import Limiter, RateLimitExceeded, get_remote_address  # type: ignore

from core.rate_limiter import rate_limit_exception_handler
from core.task_tracker import init_task_tracker
from services.embedding_service import get_embedding_service
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def _bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return int(default)


def _build_redis_client() -> Redis:
    redis_url = str(os.getenv("REDIS_URL", "")).strip()
    if redis_url:
        return Redis.from_url(redis_url)

    redis_host = str(os.getenv("REDIS_HOST", "localhost")).strip() or "localhost"
    redis_port = _int_env("REDIS_PORT", 6379)
    redis_db = _int_env("REDIS_DB", 0)
    return Redis(host=redis_host, port=redis_port, db=redis_db)


def _load_optional_router(import_path: str):
    try:
        module_path, attr = import_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[attr])
        return getattr(module, attr)
    except Exception as err:
        logger.warning(f"Optional router disabled ({import_path}): {err}")
        return None


def _make_health_router() -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health/live")
    async def health_live():
        return {"status": "alive"}

    @router.get("/health/ready")
    async def health_ready(response: Response):
        checks = {"redis": {"status": "unknown"}}
        ready = True
        try:
            redis_client = _build_redis_client()
            redis_client.ping()
            checks["redis"] = {"status": "healthy"}
        except Exception as err:
            ready = False
            checks["redis"] = {"status": "unhealthy", "error": str(err)}
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        try:
            from api.routes_cv_text_async import get_llm_runtime_state
            checks["llm_runtime"] = {"status": "healthy", "state": get_llm_runtime_state()}
        except Exception as err:
            checks["llm_runtime"] = {"status": "degraded", "error": str(err)}

        return {
            "status": "ready" if ready else "not_ready",
            "service": "recommendation",
            "mode": "text_cv",
            "checks": checks,
        }

    @router.get("/health")
    async def health_root(response: Response):
        return await health_ready(response)

    @router.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return router


app = FastAPI(
    title="TalentFlow Recommendation Service",
    description="Text-based CV analysis + recommendation APIs",
    version="1.0.0",
)


def _configure_cors(application: FastAPI) -> None:
    allowed_origins_str = str(os.getenv("ALLOWED_ORIGINS", "*")).strip() or "*"
    if allowed_origins_str == "*":
        origins = ["*"]
        allow_credentials = False
    else:
        origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
        allow_credentials = True

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


_configure_cors(app)

# Rate limiting (no-op fallback if slowapi unavailable)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)


@app.on_event("startup")
async def on_startup() -> None:
    try:
        redis_client = _build_redis_client()
        redis_client.ping()
        init_task_tracker(redis_client)
        logger.info("TaskTracker initialized (Redis)")
    except Exception as err:
        logger.warning(f"TaskTracker init failed, service remains partially available: {err}")
    try:
        await asyncio.to_thread(get_embedding_service)
        logger.info("Recommendation embedding warmup complete")
    except Exception as err:
        logger.warning(f"Recommendation embedding warmup failed: {err}")
    logger.info("Recommendation service started in text_cv mode")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Recommendation service stopped")


# Always-on stable routers
app.include_router(_make_health_router())

cv_text_router = _load_optional_router("api.routes_cv_text_async.router")
if cv_text_router is not None:
    app.include_router(cv_text_router)
else:
    logger.error("api.routes_cv_text_async.router unavailable: text CV API will be missing")

cv_ingestion_router = _load_optional_router("api.routes_cv_ingestion.router")
if cv_ingestion_router is not None:
    app.include_router(cv_ingestion_router)
else:
    logger.warning("api.routes_cv_ingestion.router unavailable: OCR ingestion API missing")

# Optional legacy routers (disabled by default)
if _bool_env("RECOMMENDATION_ENABLE_LEGACY_ROUTERS", False):
    for path in (
        "api.routes_cv_async.router",
        "api.routes_analyze.router",
        "api.routes_with_state.router",
    ):
        router = _load_optional_router(path)
        if router is not None:
            app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=str(os.getenv("HOST", "0.0.0.0")),
        port=_int_env("PORT", _int_env("API_PORT", 8001)),
        reload=_bool_env("DEBUG", False),
    )
