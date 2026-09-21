# Application FastAPI principale
# Search Engine - Etape 3

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from api.routes_search import router as search_router
from api.routes_health import router as health_router
from core.config_loader import ConfigLoader
from services.index_maintenance_state import get_maintenance_state

# Configuration
config = ConfigLoader().get_config()
api_config = config.get("api", {})

# Application
app = FastAPI(
    title="TalentFlow Search Engine",
    description="API de recherche Qdrant (semantique dense + filtres qualite/fraicheur)",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health_router)
app.include_router(search_router)


@app.middleware("http")
async def index_maintenance_guard(request: Request, call_next):
    path = request.url.path or ""
    if path.startswith("/search"):
        state = get_maintenance_state()
        if state.get("active"):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "maintenance",
                    "code": "INDEX_MAINTENANCE",
                    "message": "Indexation en cours. Patiente quelques instants puis réessaie.",
                    "retryAfterSeconds": 180,
                    "maintenance": {
                        "active": True,
                        "reason": state.get("reason") or "index_compaction",
                        "startedAt": state.get("started_at"),
                        "expectedEndAt": state.get("expected_end_at"),
                    },
                },
            )
    return await call_next(request)



@app.on_event("startup")
async def startup():
    """
    Initialisation au demarrage.
    """
    logger.info("Search Engine demarre")


@app.on_event("shutdown")
async def shutdown():
    """
    Nettoyage a l'arret.
    """
    logger.info("Search Engine arrete")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=api_config.get("host", "0.0.0.0"),
        port=int(api_config.get("port", 8002)),
        reload=api_config.get("debug", False),
    )
