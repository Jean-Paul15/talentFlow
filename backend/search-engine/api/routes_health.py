# Routes de sante et administration

import json
import os
from typing import Optional, Set
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Query
from loguru import logger

from api.schemas import HealthResponse
from core.mongo_reader import MongoReader
from services.runtime_state import get_search_service
from services.qdrant_index_manager import QdrantIndexManager
from services.document_builder import build_canonical_job_identity, is_probable_job_document
from services.index_maintenance_state import get_maintenance_state, set_maintenance

router = APIRouter(tags=["health"])


def _notify_runtime_jobs_changed(stats: dict) -> dict:
    """
    Informe l'API gateway qu'un nouveau stock d'offres est disponible.
    Cette notification ne doit jamais faire echouer la reindexation.
    """
    base_url = str(os.getenv("API_GATEWAY_URL", "http://api-gateway:3000")).strip().rstrip("/")
    if not base_url:
        return {"ok": False, "reason": "api_gateway_url_missing"}

    indexed = int(stats.get("indexed", 0) or 0)
    marked = int(stats.get("marked", 0) or 0)
    errors = int(stats.get("errors", 0) or 0)
    if indexed <= 0 and marked <= 0 and errors <= 0:
        return {"ok": True, "skipped": True, "reason": "no_material_change"}

    payload = json.dumps({"domains": ["jobs", "recommendation"]}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    internal_token = str(os.getenv("RUNTIME_INTERNAL_TOKEN", "")).strip()
    if internal_token:
        headers["x-internal-token"] = internal_token

    request = Request(
        f"{base_url}/runtime/cache-version/bump",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            body = response.read().decode("utf-8", errors="ignore")
        parsed = json.loads(body) if body else {}
        return {
            "ok": True,
            "status": getattr(response, "status", 200),
            "response": parsed,
        }
    except HTTPError as err:
        detail = err.read().decode("utf-8", errors="ignore")
        logger.warning(f"Runtime cache bump failed with HTTP {err.code}: {detail}")
        return {"ok": False, "status": err.code, "detail": detail or str(err)}
    except URLError as err:
        logger.warning(f"Runtime cache bump failed: {err}")
        return {"ok": False, "detail": str(err.reason)}
    except Exception as err:
        logger.warning(f"Runtime cache bump failed unexpectedly: {err}")
        return {"ok": False, "detail": str(err)}


def _count_qdrant_unique_candidates(mongo: MongoReader) -> int:
    """
    Qdrant dedup plusieurs offres vers un point canonique unique.
    Le sync-status doit comparer Mongo "indexable + dedup" contre points Qdrant,
    sinon il force des reindex inutiles en boucle.
    """
    seen: Set[str] = set()
    count = 0
    for job in mongo.stream_jobs(batch_size=500):
        if not is_probable_job_document(job):
            continue
        identity = build_canonical_job_identity(job)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        count += 1
    return count


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Verifie l'etat de sante du service.
    """
    qdrant_ok = False
    index_exists = False
    doc_count = 0
    backend_name = "qdrant"
    reranker_available = False
    reranker_loaded = False
    reranker_enabled_default = False
    reranker_model = None
    
    try:
        service = get_search_service()
        backend_health = service.health()
        backend_name = backend_health.get("backend", "qdrant")
        qdrant_ok = bool(backend_health.get("qdrant", False))
        index_exists = bool(backend_health.get("index_exists", False))
        doc_count = int(backend_health.get("doc_count", 0))
        reranker_available = bool(backend_health.get("reranker_available", False))
        reranker_loaded = bool(backend_health.get("reranker_loaded", False))
        reranker_enabled_default = bool(backend_health.get("reranker_enabled_default", False))
        reranker_model = backend_health.get("reranker_model")
    except Exception as err:
        logger.warning(f"Health check erreur: {err}")
    
    return HealthResponse(
        status="healthy" if qdrant_ok else "degraded",
        elasticsearch=False,
        qdrant=qdrant_ok,
        search_backend=backend_name,
        index_exists=index_exists,
        doc_count=doc_count,
        reranker_available=reranker_available,
        reranker_loaded=reranker_loaded,
        reranker_enabled_default=reranker_enabled_default,
        reranker_model=reranker_model,
    )


@router.post("/index/create")
async def create_index(force: bool = False):
    """
    Cree la collection Qdrant selon le backend actif.
    """
    manager = QdrantIndexManager()
    created = manager.create_collection(force=force)
    return {
        "created": created,
        "backend": "qdrant",
        "index": manager.collection_name,
    }


@router.post("/index/reindex")
async def reindex_jobs(force: bool = False):
    """
    Lance une indexation depuis MongoDB vers Qdrant.
    """
    from services.job_indexer_qdrant import QdrantJobIndexer
    indexer = QdrantJobIndexer()
    stats = indexer.index_all(reindex=force)
    cache_bump = _notify_runtime_jobs_changed(stats)
    return {
        "backend": "qdrant",
        "stats": stats,
        "collection": indexer.collection_name,
        "mode": stats.get("mode"),
        "cache_bump": cache_bump,
    }




@router.get("/index/maintenance/status")
async def index_maintenance_status():
    """Retourne l'état de maintenance indexation."""
    return get_maintenance_state()


@router.post("/index/maintenance/start")
async def start_index_maintenance(
    reason: str = Query(default="nightly_compaction"),
    duration_minutes: int = Query(default=60, ge=1, le=360),
):
    """Active le mode maintenance pour bloquer les recherches utilisateur pendant compaction."""
    state = set_maintenance(True, reason=reason, duration_minutes=duration_minutes)
    return {"ok": True, "maintenance": state}


@router.post("/index/maintenance/end")
async def end_index_maintenance(reason: str = Query(default="completed")):
    """Désactive le mode maintenance indexation."""
    state = set_maintenance(False, reason=reason)
    return {"ok": True, "maintenance": state}

@router.get("/index/sync-status")
async def search_index_sync_status():
    """
    Compare la source Mongo (Silver) et l'index de recherche (ES/Qdrant).
    Sert de base pour les décisions d'automatisation (skip/reindex).
    """
    service = get_search_service()
    backend_health = service.health()

    mongo_ok = False
    mongo_count = 0
    mongo_effective_index_count: Optional[int] = None
    delta_pending_count = None
    mongo_error = None
    try:
        mongo = MongoReader()
        mongo_count = int(mongo.count_jobs())
        if backend_health.get("backend") == "qdrant":
            mongo_effective_index_count = _count_qdrant_unique_candidates(mongo)
        delta_pending_count = int(mongo.count_jobs_delta(backend_health.get("backend", "qdrant")))
        mongo_ok = True
    except Exception as err:
        mongo_error = str(err)
        logger.warning(f"Sync-status Mongo indisponible: {err}")

    index_count = int(backend_health.get("doc_count", 0) or 0)
    index_exists = bool(backend_health.get("index_exists", False))
    backend_name = backend_health.get("backend", "qdrant")

    comparable_mongo_count = mongo_effective_index_count if mongo_effective_index_count is not None else mongo_count
    drift = comparable_mongo_count - index_count if mongo_ok else None
    abs_drift = abs(drift) if drift is not None else None
    drift_ratio = (
        (abs_drift / max(comparable_mongo_count, 1))
        if (mongo_ok and abs_drift is not None)
        else None
    )
    backend_ok = bool(backend_health.get("ok", False))
    positive_drift = (mongo_ok and drift is not None and drift > 0)
    # Drift faible = ecart tolere (ex: documents non indexables filtres par qualité).
    positive_drift_material = bool(
        positive_drift
        and drift_ratio is not None
        and float(drift_ratio) > 0.02
    )
    negative_drift = (mongo_ok and drift is not None and drift < 0)
    pending_delta = (mongo_ok and delta_pending_count is not None and delta_pending_count > 0)

    # L'automatisation quotidienne doit privilégier le delta. Un index plus "grand" que Mongo
    # (stale docs possibles) ne force plus un reindex immédiat pour éviter les boucles.
    full_reindex_recommended = bool(negative_drift and not pending_delta)
    needs_reindex = (
        (not index_exists)
        or (not backend_ok)
        or bool(pending_delta)
        or bool(positive_drift_material)
    )

    return {
        "backend": backend_name,
        "backend_ok": backend_ok,
        "index_exists": index_exists,
        "index_count": index_count,
        "mongo_ok": mongo_ok,
        "mongo_count": mongo_count,
        "mongo_effective_index_count": mongo_effective_index_count,
        "delta_pending_count": delta_pending_count,
        "mongo_error": mongo_error,
        "drift_count": drift,
        "drift_abs": abs_drift,
        "drift_ratio": drift_ratio,
        "needs_reindex": bool(needs_reindex),
        "full_reindex_recommended": full_reindex_recommended,
        "reason": (
            "backend_unhealthy" if not backend_ok
            else "index_missing" if not index_exists
            else "delta_pending" if pending_delta
            else "missing_docs_in_index" if positive_drift_material
            else "stale_docs_possible" if full_reindex_recommended
            else "in_sync"
        ),
    }
