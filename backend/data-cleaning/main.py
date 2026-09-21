# Point d'entrée FastAPI - Data Cleaning Service
# Étape 2: Nettoyage + NER + Enrichissement

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from typing import List, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel
from run_pipeline import main as run_pipeline_main
from pipeline import CleaningPipeline
from core.config_loader import ConfigLoader
from core.minio_reader import MinioReader
from core.mongo_writer import MongoWriter

# Modèles
class CleanRequest(BaseModel):
    """Requête de nettoyage"""
    job_ids: Optional[List[str]] = None
    since_hours: int = 24
    full: bool = False
    site_filter: Optional[str] = None

class CleanResponse(BaseModel):
    """Réponse du nettoyage"""
    status: str
    cleaned_count: int
    skipped_count: int
    errors: int
    processed_jobs: List[str]

# Application FastAPI
app = FastAPI(
    title="TalentFlow Data Cleaning",
    description="Service de nettoyage et enrichissement - Étape 2",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clients
config = ConfigLoader().get_config()
minio_reader = MinioReader()
mongo_writer = MongoWriter()

@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    logger.info("Data Cleaning Service démarre")
    try:
        # Vérifier MinIO
        buckets = minio_reader.client.list_buckets()
        logger.info(f"MinIO connecté - Bronze bucket trouvé")
        # Vérifier MongoDB
        count = mongo_writer.count_jobs()
        logger.info(f"MongoDB connecté - {count} offres existantes")
    except Exception as e:
        logger.error(f"Erreur connexion services: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    logger.info("Data Cleaning Service s'arrête")

@app.get("/health")
async def health_check():
    """Vérifier santé du service"""
    try:
        # Ping MinIO
        minio_reader.client.list_buckets()
        # Ping MongoDB
        mongo_writer.count_jobs()
        return {"status": "healthy", "service": "data-cleaning"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/clean", response_model=CleanResponse)
async def clean_jobs(request: CleanRequest, background_tasks: BackgroundTasks):
    """
    Lance le nettoyage des offres.
    
    Récupère les offres depuis MinIO (Bronze), applique:
    - Nettoyage texte
    - Déduplication (hash)
    - NER (extraction skills)
    - Enrichissement IA
    - Sauvegarde MongoDB (Silver)
    
    Args:
        request: Configuration du nettoyage
        background_tasks: Tâches en arrière-plan
    
    Returns:
        CleanResponse avec statistiques
    """
    try:
        logger.info(f"Démarrage nettoyage")
        
        # Initialiser pipeline
        pipeline = CleaningPipeline()
        
        # Déterminer les offres à traiter
        since_date = None
        if not request.full:
            since_date = datetime.utcnow() - timedelta(hours=request.since_hours)
        
        # Exécuter le pipeline
        stats = pipeline.run(
            since_date=since_date,
            site_prefix=request.site_filter
        )
        
        processed_ids = _get_cleaned_job_ids(stats.get("processed", 0))
        
        logger.info(
            f"Nettoyage terminé: "
            f"{stats.get('processed', 0)} traitées, "
            f"{stats.get('skipped', 0)} ignorées, "
            f"{stats.get('errors', 0)} erreurs"
        )
        
        return CleanResponse(
            status="success",
            cleaned_count=stats.get("processed", 0),
            skipped_count=stats.get("skipped", 0),
            errors=stats.get("errors", 0),
            processed_jobs=processed_ids
        )
    
    except Exception as e:
        logger.error(f"Erreur nettoyage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clean-specific")
async def clean_specific_jobs(job_ids: List[str]):
    """
    Nettoie des offres spécifiques.
    
    Args:
        job_ids: IDs des offres à nettoyer
    
    Returns:
        Statistiques de nettoyage
    """
    try:
        logger.info(f"Nettoyage spécifique: {len(job_ids)} offres")
        
        pipeline = CleaningPipeline()
        
        # Récupérer les offres brutes
        raw_jobs = _get_raw_jobs_from_minio(job_ids)
        
        cleaned_count = 0
        errors = 0
        cleaned_ids = []
        
        for raw_job in raw_jobs:
            try:
                cleaned_job = pipeline.process_job(raw_job)
                if cleaned_job:
                    mongo_writer.insert_job(cleaned_job)
                    cleaned_ids.append(cleaned_job["_id"])
                    cleaned_count += 1
            except Exception as e:
                logger.error(f"Erreur nettoyage {raw_job.get('_id', 'unknown')}: {e}")
                errors += 1
        
        return {
            "status": "success",
            "cleaned_count": cleaned_count,
            "errors": errors,
            "cleaned_ids": cleaned_ids
        }
    
    except Exception as e:
        logger.error(f"Erreur nettoyage spécifique: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def cleaning_status():
    """Statut du service"""
    try:
        mongo_count = mongo_writer.count_jobs()
        bronze_pending = len(minio_reader.list_new_objects())
        return {
            "status": "running",
            "service": "data-cleaning",
            "jobs_in_mongodb": mongo_count,
            "bronze_pending_objects": bronze_pending,
            "processing": "text-clean, ner, skill-extraction, llm-enrichment",
            "llm_provider_primary": "mistral",
            "llm_provider_fallback": "ner_patterns",
            "output": "mongodb-silver"
        }
    except Exception as e:
        return {"status": "running", "error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Statistiques du pipeline"""
    try:
        total_jobs = mongo_writer.count_jobs()
        
        # Compter par source
        collection = mongo_writer.collection
        sources = collection.distinct("source_name")

        source_counts = {}
        for source in sources:
            source_counts[source] = collection.count_documents({"source_name": source})

        expired_count = collection.count_documents({"is_expired": True})
        stale_count = collection.count_documents({"is_stale": True})
        low_quality_count = collection.count_documents({"quality_score": {"$lt": 0.4}})

        avg_quality = 0.0
        quality_rows = list(
            collection.aggregate(
                [
                    {"$match": {"quality_score": {"$type": "number"}}},
                    {"$group": {"_id": None, "avg_quality_score": {"$avg": "$quality_score"}}},
                ]
            )
        )
        if quality_rows:
            avg_quality = float(quality_rows[0].get("avg_quality_score") or 0.0)
        
        return {
            "total_cleaned_jobs": total_jobs,
            "by_source": source_counts,
            "expired_count": expired_count,
            "stale_count": stale_count,
            "low_quality_count": low_quality_count,
            "avg_quality_score": round(avg_quality, 4),
            "processing_pipeline": [
                "1. Text cleaning (remove HTML, normalize spaces)",
                "2. Deduplication (hash-based)",
                "3. NER (skill extraction)",
                "4. LLM enrichment (Mistral principal)",
                "5. Fallback extraction (NER + patterns)",
                "6. MongoDB storage"
            ]
        }
    
    except Exception as e:
        logger.error(f"Erreur statistiques: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs")
async def list_cleaned_jobs(
    limit: int = 50,
    skip: int = 0,
    source: Optional[str] = None,
    q: Optional[str] = None,
    country: Optional[str] = None,
    stale: Optional[bool] = None,
    expired: Optional[bool] = None,
    min_quality: Optional[float] = None,
):
    """
    Liste paginée des offres nettoyées stockées dans MongoDB (Silver).
    Endpoint dédié au dashboard sourcing-only.
    """
    try:
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200
        if skip < 0:
            skip = 0

        query = {}
        if source:
            query["source_name"] = source
        if country:
            query["country"] = country
        if stale is not None:
            query["is_stale"] = bool(stale)
        if expired is not None:
            query["is_expired"] = bool(expired)
        if min_quality is not None:
            query["quality_score"] = {"$gte": float(min_quality)}
        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"company": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]

        collection = mongo_writer.collection
        total = collection.count_documents(query)
        cursor = (
            collection.find(query)
            .sort([("processed_at", -1), ("scraped_at", -1)])
            .skip(skip)
            .limit(limit)
        )

        items = []
        for doc in cursor:
            doc["_id"] = str(doc.get("_id", ""))
            items.append(doc)

        sources = sorted([s for s in collection.distinct("source_name") if s])
        countries = sorted([c for c in collection.distinct("country") if c])

        return {
            "status": "success",
            "total": total,
            "skip": skip,
            "limit": limit,
            "count": len(items),
            "sources": sources,
            "countries": countries,
            "items": items,
        }
    except Exception as e:
        logger.error(f"Erreur lecture jobs nettoyés: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Utilitaires
def _get_cleaned_job_ids(count: int) -> List[str]:
    """Récupère les IDs des offres nettoyées (stub)"""
    # En réalité, il faudrait tracker ces IDs
    return [f"job_cleaned_{i}" for i in range(min(count, 10))]

def _get_raw_jobs_from_minio(job_ids: List[str]) -> List[dict]:
    """Récupère les offres brutes depuis MinIO"""
    import json
    raw_jobs = []
    bucket = minio_reader.bucket
    
    for job_id in job_ids:
        try:
            # Chercher dans MinIO
            objects = minio_reader.client.list_objects(bucket, recursive=True)
            for obj in objects:
                if job_id in obj.object_name:
                    # Lire l'objet
                    response = minio_reader.client.get_object(bucket, obj.object_name)
                    data = json.loads(response.read().decode())
                    raw_jobs.append(data)
                    break
        except Exception as e:
            logger.error(f"Erreur récupération {job_id}: {e}")
    
    return raw_jobs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
    )
