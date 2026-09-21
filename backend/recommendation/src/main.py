# Étape 4: Main app - Minimal et rapide
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from .api.controllers import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="TalentFlow RAG",
    description="Étape 4: Gemini-backed RAG Engine",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Middleware sécurité + performance
# CORS: Ouvert pour mobile + dev, contrôlé en prod
import os

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_str == "*":
    cors_origins = ["*"]
    allow_credentials = False
else:
    cors_origins = allowed_origins_str.split(",")
    allow_credentials = True

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Mobile friendly
)
app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["POST", "GET", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Mobile friendly
)

app.include_router(router)

@app.on_event("startup")
async def startup():
    """Init rapide au demarrage"""
    from .core.di import DIContainer
    DIContainer()
    logging.info("App startup complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        workers=2,  # Limit workers = rapide
        loop="uvloop",  # Fast event loop
        access_log=False
    )
