# Point d'entrée FastAPI - Job Sourcing Service
# Étape 1: Web Scraping avec Scrapy

import os
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pydantic import BaseModel
from run_spider import (
    run_all, run_spider,
    SPIDERS, MAX_WORKERS,
)
from core.minio_client import MinioStorageClient
from core.redis_client import RedisFingerprint
from core.kafka_producer import KafkaJobProducer
from core.orchestration_settings import (
    get_orchestration_settings,
    update_orchestration_settings,
)
from core.registry_constants import (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_NIGHTLY,
    PRIORITY_LABELS,
)
from core.sourcing_reports import (
    append_scrape_report,
    build_qa_summary,
    latest_report_per_spider,
    read_scrape_reports,
)
from core.autopilot_planner import build_autoplan
from core.source_bandit import reset_bandit, snapshot_bandit
from core.qa_alerting import build_qa_alert_preview, run_qa_alert_check
from core.sites_registry import (
    get_all_sites,
    get_schedule_info,
    get_airflow_dag_config,
    get_deep_crawler_sites,
    get_spider_sites,
    get_api_sites,
    SITES_REGISTRY,
)
from core.registry_access import get_sites_by_priority

AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow:8080").rstrip("/")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
AIRFLOW_API_TIMEOUT = int(os.getenv("AIRFLOW_API_TIMEOUT", "20"))

# Modèles
class ScrapeRequest(BaseModel):
    """Requête de scraping"""
    sites: Optional[List[str]] = None
    full: bool = False
    
class ScrapeResponse(BaseModel):
    """Réponse du scraping"""
    status: str
    job_ids: List[str]
    count: int
    errors: int


class OrchestrationSettingsRequest(BaseModel):
    """Mise a jour de la programmation Airflow."""
    priority_crons: Optional[Dict[str, str]] = None
    dag_enabled: Optional[Dict[str, bool]] = None


class DagPauseRequest(BaseModel):
    """Etat pause/reprise d'un DAG."""
    paused: bool


class DagTriggerRequest(BaseModel):
    """Declenchement manuel d'un DAG."""
    conf: Optional[Dict[str, object]] = None

# Application FastAPI
app = FastAPI(
    title="TalentFlow Job Sourcing",
    description="Service de scraping web - Étape 1",
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
minio_client = MinioStorageClient()
redis_client = RedisFingerprint()
kafka_producer = KafkaJobProducer()

@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    logger.info("Job Sourcing Service démarre")
    try:
        if kafka_producer.is_ready():
            logger.info("Kafka connecté - publication events active")
        else:
            logger.warning("Kafka non disponible au startup")

        # MinIO reste utile pour la purge/inspection Bronze
        buckets = minio_client.list_buckets()
        logger.info(f"MinIO connecté - {len(buckets)} buckets trouvés")
    except Exception as e:
        logger.error(f"Erreur startup: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    logger.info("Job Sourcing Service s'arrête")

@app.get("/health")
async def health_check():
    """Vérifier santé du service"""
    try:
        # Ping Redis
        redis_client.redis.ping()
        kafka_ok = kafka_producer.is_ready()
        return {
            "status": "healthy" if kafka_ok else "degraded",
            "service": "job-sourcing",
            "kafka": kafka_ok,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_jobs(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Lance le scraping web.
    
    Execute les Scrapy spiders et publie les offres sur Kafka.
    """
    try:
        requested_targets = request.sites or list(get_all_sites().keys())
        spider_targets, api_sources = _resolve_targets(requested_targets)
        logger.info(
            f"Demarrage scraping: spiders={spider_targets}, "
            f"api_sources={api_sources}"
        )

        # Mode arriere-plan (full crawl)
        if request.full:
            background_tasks.add_task(run_all)
            return ScrapeResponse(
                status="scheduled",
                job_ids=[],
                count=0,
                errors=0
            )
        
        # Mode synchrone - spider par spider
        total_items = 0
        total_errors = 0

        for spider_name in spider_targets:
            result = await run_in_threadpool(run_spider, spider_name)
            items_count = result.get("items", 0)
            total_items += items_count
            total_errors += result.get("errors", 0)
            logger.info(
                f"Spider {spider_name}: {items_count} scrapes, "
                f"{result.get('errors', 0)} erreurs"
            )

        if api_sources:
            api_result = await run_in_threadpool(
                _run_api_collection, source_ids=api_sources,
            )
            total_items += api_result.get("items", 0)
            total_errors += api_result.get("errors", 0)

        logger.info(f"Scraping termine: {total_items} items, {total_errors} erreurs")
        
        return ScrapeResponse(
            status="success",
            job_ids=[],
            count=total_items,
            errors=total_errors
        )
    
    except Exception as e:
        logger.error(f"Erreur scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def scraping_status():
    """Statut du service"""
    bandit = snapshot_bandit()
    return {
        "status": "running",
        "service": "job-sourcing",
        "mode": "parallel",
        "parallel_workers": MAX_WORKERS,
        "spiders_available": list(SPIDERS.keys()),
        "ingestion": "kafka",
        "kafka_topic": kafka_producer.topic,
        "deduplication": "redis",
        "bandit": {
            "policy": bandit.get("policy"),
            "epsilon": bandit.get("epsilon"),
            "tracked_targets": bandit.get("tracked_targets"),
            "avg_reward_global": bandit.get("avg_reward_global"),
            "updated_at": bandit.get("updated_at"),
        },
    }


@app.get("/api/scrape/reports")
async def scrape_reports(
    limit: int = Query(50, ge=1, le=500),
    spider: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
):
    """Historique recent des runs de scraping (JSONL local)."""
    reports = read_scrape_reports(
        limit=limit,
        spider=spider,
        status=status,
        source_type=source_type,
    )
    return {
        "total": len(reports),
        "limit": limit,
        "filters": {
            "spider": spider,
            "status": status,
            "source_type": source_type,
        },
        "reports": reports,
    }


@app.get("/api/scrape/reports/latest")
async def scrape_reports_latest(
    per_spider: int = Query(1, ge=1, le=10),
    include_api: bool = True,
):
    """Dernier(s) run(s) par spider/source pour un dashboard rapide."""
    grouped = latest_report_per_spider(
        limit_per_spider=per_spider,
        include_api=include_api,
    )
    return {
        "per_spider": per_spider,
        "include_api": include_api,
        "spiders": grouped,
    }


@app.get("/api/scrape/qa")
async def scrape_qa_summary(limit: int = Query(200, ge=10, le=1000)):
    """Resume QA des sources (couverture dates/apply/description, runs recents)."""
    return build_qa_summary(limit=limit)


@app.get("/api/scrape/qa-alerts/preview")
async def scrape_qa_alerts_preview(limit: int = Query(300, ge=50, le=2000)):
    """Prévisualise les alertes QA qui seraient émises (sans envoi)."""
    return build_qa_alert_preview(limit=limit)


@app.post("/api/scrape/qa-alerts/check")
async def scrape_qa_alerts_check(
    limit: int = Query(300, ge=50, le=2000),
    notify: bool = True,
    force: bool = False,
):
    """
    Vérifie la QA récente et envoie des alertes Telegram/Email si des seuils chutent.
    Anti-spam via cooldown par spider/issue.
    """
    return await run_in_threadpool(
        lambda: run_qa_alert_check(limit=limit, notify=notify, force=force)
    )


@app.get("/api/scrape/autoplan")
async def scrape_autoplan(
    max_targets: int = Query(5, ge=1, le=50),
    include_deferred: bool = True,
    lookback_reports: int = Query(400, ge=50, le=5000),
    force: bool = False,
):
    """
    Plan adaptatif (sans execution) : choisit les sources a relancer automatiquement
    selon priorite, fraicheur, erreurs et qualite des donnees.
    """
    return build_autoplan(
        max_targets=max_targets,
        include_deferred=include_deferred,
        lookback_reports=lookback_reports,
        force=force,
    )


@app.get("/api/scrape/bandit")
async def scrape_bandit_snapshot():
    """Etat du bandit de priorisation des sources (persiste sur volume)."""
    return snapshot_bandit()


@app.post("/api/scrape/bandit/reset")
async def scrape_bandit_reset():
    """Reset manuel du bandit (ops/debug)."""
    return {"status": "ok", "bandit": reset_bandit()}


@app.post("/api/scrape/autopilot/run")
async def scrape_autopilot_run(
    background_tasks: BackgroundTasks,
    background: bool = True,
    max_targets: int = Query(5, ge=1, le=50),
    lookback_reports: int = Query(400, ge=50, le=5000),
    force: bool = False,
):
    """
    Execute automatiquement les cibles "dues" decidees par l'autoplan.
    Le systeme choisit quoi lancer; l'operateur n'a plus a choisir les spiders.
    """
    plan = build_autoplan(
        max_targets=max_targets,
        include_deferred=False,
        lookback_reports=lookback_reports,
        force=force,
    )
    selected = list(plan.get("selected") or [])
    if not selected:
        return {
            "status": "skipped",
            "mode": "background" if background else "sync",
            "reason": "no_due_targets",
            **plan,
            "count": 0,
            "errors": 0,
            "executed_count": 0,
        }

    if background:
        background_tasks.add_task(_run_autopilot_targets, selected)
        return {
            "status": "scheduled",
            "mode": "background",
            **plan,
            "count": 0,
            "errors": 0,
            "executed_count": len(selected),
        }

    execution = await run_in_threadpool(_execute_autopilot_targets_sync, selected)
    return {
        "status": execution.get("status", "success"),
        "mode": "sync",
        **plan,
        **execution,
    }


@app.post("/api/scrape/priority/{priority_ref}")
async def scrape_by_priority(
    priority_ref: str,
    background_tasks: BackgroundTasks,
    background: bool = True,
):
    """
    Lance un scraping par priorite (high|medium|low|nightly ou 1..4).
    Utilise le registre pour resoudre les sites, puis spiders/APIs.
    """
    priority = _parse_priority_ref(priority_ref)
    sites = get_sites_by_priority(priority)
    if not sites:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun site actif pour la priorite {priority_ref}",
        )

    requested_targets = list(sites.keys())
    spider_targets, api_sources = _resolve_targets(requested_targets)

    if background:
        if spider_targets:
            background_tasks.add_task(_run_sites_sequence, spider_targets)
        if api_sources:
            background_tasks.add_task(_run_api_collection, api_sources)
        return {
            "status": "scheduled",
            "mode": "background",
            "priority": priority,
            "priority_label": PRIORITY_LABELS.get(priority),
            "sites": requested_targets,
            "spiders": spider_targets,
            "api_sources": api_sources,
        }

    total_items = 0
    total_errors = 0
    spider_results = {}
    for spider_name in spider_targets:
        result = await run_in_threadpool(run_spider, spider_name)
        spider_results[spider_name] = result
        total_items += int(result.get("items", 0))
        total_errors += int(result.get("errors", 0))
    api_result = None
    if api_sources:
        api_result = await run_in_threadpool(_run_api_collection, source_ids=api_sources)
        total_items += int(api_result.get("items", 0))
        total_errors += int(api_result.get("errors", 0))

    return {
        "status": "success" if total_errors == 0 else "partial",
        "mode": "sync",
        "priority": priority,
        "priority_label": PRIORITY_LABELS.get(priority),
        "sites": requested_targets,
        "spiders": spider_results,
        "api_result": api_result,
        "count": total_items,
        "errors": total_errors,
    }

@app.post("/api/deduplicate-check")
async def check_duplicates(job_ids: List[str]):
    """
    Verifie quels offres sont deja connues (duplicates).
    
    Args:
        job_ids: IDs a verifier
    
    Returns:
        Dict avec offres nouvelles et doublons
    """
    try:
        new_jobs = []
        duplicates = []
        
        for job_id in job_ids:
            if redis_client.exists(job_id):
                duplicates.append(job_id)
            else:
                new_jobs.append(job_id)
        
        logger.info(f"Dedup check: {len(new_jobs)} nouvelles, {len(duplicates)} doublons")
        
        return {
            "new_jobs": new_jobs,
            "duplicates": duplicates,
            "total_checked": len(job_ids)
        }
    
    except Exception as e:
        logger.error(f"Erreur deduplication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/purge")
async def purge_all():
    """
    Vide le data lake Bronze : Redis (fingerprints) + MinIO (bronze).
    Reinitialisation complete avant un nouveau crawl.
    """
    try:
        # 1. Vider Redis (fingerprints)
        redis_ok = redis_client.clear()
        redis_stats = redis_client.get_stats()

        # 2. Vider MinIO (bucket bronze ecrit par Spark)
        minio_result = minio_client.clear_bucket()

        logger.info(
            f"Purge complete: Redis={redis_ok}, "
            f"MinIO={minio_result['deleted']} supprimes"
        )

        return {
            "status": "purged",
            "redis": {
                "cleared": redis_ok,
                "remaining_keys": redis_stats.get("total_keys", 0),
            },
            "minio": minio_result,
            "kafka": {
                "topic": kafka_producer.topic,
                "note": "Les messages Kafka deja publies ne sont pas supprimes via cette API.",
            },
        }

    except Exception as e:
        logger.error(f"Erreur purge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/purge-and-rescrape")
async def purge_and_rescrape(
    request: ScrapeRequest, background_tasks: BackgroundTasks,
):
    """
    Vide Bronze (Redis + MinIO) puis relance le scraping complet.
    Operation atomique : purge + rescrape en arriere-plan.
    """
    try:
        # 1. Purge
        redis_client.clear()
        minio_result = minio_client.clear_bucket()

        logger.info(
            f"Purge terminee, MinIO: {minio_result['deleted']} supprimes. "
            "Lancement du rescrape..."
        )

        # 2. Rescrape en arriere-plan
        requested_targets = request.sites or list(get_all_sites().keys())
        spider_targets, api_sources = _resolve_targets(requested_targets)
        background_tasks.add_task(_run_sites_sequence, spider_targets)
        if api_sources:
            background_tasks.add_task(_run_api_collection, api_sources)

        return {
            "status": "purged_and_scheduled",
            "purge": {"minio_deleted": minio_result["deleted"]},
            "scrape": {
                "spiders": spider_targets,
                "api_sources": api_sources,
                "mode": "background",
            },
        }

    except Exception as e:
        logger.error(f"Erreur purge+rescrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/collect")
async def collect_api_jobs(background_tasks: BackgroundTasks):
    """
    Lance la collecte d'offres via APIs gratuites (JSearch, Adzuna).
    Les cles API doivent etre configurees dans .env.
    """
    try:
        api_sites = get_api_sites()
        if not api_sites:
            return {
                "status": "skipped",
                "message": "Aucune source API active dans le registre",
            }

        background_tasks.add_task(_run_api_collection)
        return {
            "status": "scheduled",
            "sources": list(api_sites.keys()),
            "message": "Collecte API lancee en arriere-plan",
        }
    except Exception as e:
        logger.error(f"Erreur collecte API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Statistiques detaillees du pipeline sourcing."""
    try:
        redis_stats = redis_client.get_stats()
        minio_count = minio_client.count_objects()
        return {
            "redis": redis_stats,
            "kafka": {
                "enabled": kafka_producer.is_ready(),
                "topic": kafka_producer.topic,
                "bootstrap_servers": kafka_producer.bootstrap_servers,
            },
            "minio": {
                "bucket": minio_client.bucket_name,
                "bronze_objects": minio_count,
                "bronze_pending_objects": minio_count,
                "note": "Objets en attente de cleaning dans Bronze (queue de travail)",
            },
            "spiders": list(SPIDERS.keys()),
        }
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sites")
async def list_sites():
    """Liste complete de tous les sites du registre avec metadata."""
    sites = get_all_sites()
    api_sites = get_api_sites()
    return {
        "total": len(sites),
        "with_spider": len(get_spider_sites()),
        "deep_crawler": len(get_deep_crawler_sites()),
        "api_sources": len(api_sites),
        "sites": {
            site_id: {
                "label": info["label"],
                "url": info["url"],
                "pays": info["pays"],
                "category": info["category"],
                "spider": info.get("spider") or "deep_crawler",
                "source": info.get("source", "scraping"),
                "source_type": info.get("source_type", info.get("source", "scraping")),
                "active": info.get("active", True),
                "priority": info["priority"],
                "schedule_priority": info.get("schedule_priority", info["priority"]),
                "freshness_ttl_days": info.get("freshness_ttl_days"),
                "country_bias": info.get("country_bias"),
                "supports_deadline": info.get("supports_deadline"),
                "supports_apply_url": info.get("supports_apply_url"),
                "extraction_hints": info.get("extraction_hints", {}),
                "api_provider": info.get("api_provider"),
                "has_dedicated_folder": _has_dedicated_folder(info),
            }
            for site_id, info in sites.items()
        },
    }


@app.get("/api/schedule")
async def get_schedule():
    """
    Horaires d'orchestration Airflow pour chaque site.
    Retourne la planification complete : cron, heures, frequence.
    """
    return {
        "sites": get_schedule_info(),
        "dags": get_airflow_dag_config(),
        "settings": get_orchestration_settings(),
    }


@app.get("/api/orchestration/settings")
async def orchestration_settings():
    """Retourne la configuration d'orchestration modifiable depuis le front."""
    return get_orchestration_settings()


@app.put("/api/orchestration/settings")
async def set_orchestration_settings(request: OrchestrationSettingsRequest):
    """Met a jour les crons et l'etat active/desactive des DAGs."""
    try:
        updated = update_orchestration_settings(
            priority_crons=request.priority_crons,
            dag_enabled=request.dag_enabled,
        )
        return {"status": "updated", "settings": updated}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.error(f"Erreur maj orchestration: {err}")
        raise HTTPException(status_code=500, detail=str(err)) from err


@app.get("/api/orchestration/dags")
async def list_airflow_dags():
    """Expose la liste des DAGs Airflow via l'API REST Airflow."""
    return await _airflow_api_request("GET", "/api/v1/dags?limit=100")


@app.patch("/api/orchestration/dags/{dag_id}/pause")
async def pause_airflow_dag(dag_id: str, request: DagPauseRequest):
    """Met un DAG en pause ou le reactive."""
    payload = {"is_paused": request.paused}
    data = await _airflow_api_request(
        "PATCH", f"/api/v1/dags/{dag_id}", payload,
    )
    return {"status": "ok", "dag_id": dag_id, "paused": request.paused, "data": data}


@app.post("/api/orchestration/dags/{dag_id}/trigger")
async def trigger_airflow_dag(dag_id: str, request: DagTriggerRequest):
    """Declenche immediatement un DAG."""
    payload = {"conf": request.conf or {}}
    data = await _airflow_api_request(
        "POST", f"/api/v1/dags/{dag_id}/dagRuns", payload,
    )
    return {"status": "triggered", "dag_id": dag_id, "data": data}


def _run_sites_sequence(sites: List[str]):
    """Execute les spiders en PARALLELE (tache arriere-plan)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    valid = [s for s in sites if s in SPIDERS]
    logger.info(
        f"Rescrape parallele: {len(valid)} spiders, "
        f"{MAX_WORKERS} workers"
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_spider, site): site
            for site in valid
        }
        for future in as_completed(futures):
            site = futures[future]
            try:
                result = future.result()
                logger.info(
                    f"Rescrape {site}: {result.get('items', 0)} items"
                )
            except Exception as err:
                logger.error(f"Rescrape {site}: erreur - {err}")

    logger.info(f"Rescrape termine: {len(valid)} sites traites")


def _run_autopilot_targets(selected: List[dict[str, Any]]) -> None:
    """Execution arriere-plan du plan autopilot (best-effort)."""
    result = _execute_autopilot_targets_sync(selected)
    logger.info(
        "Autopilot execute en arriere-plan: "
        f"{result.get('executed_count', 0)} cibles, "
        f"{result.get('count', 0)} items, {result.get('errors', 0)} erreurs"
    )


def _execute_autopilot_targets_sync(selected: List[dict[str, Any]]) -> dict[str, Any]:
    """
    Execute une liste de cibles planifiees par l'autoplan.
    Chaque entree correspond a un spider dedie ou a api_aggregator.
    """
    total_items = 0
    total_errors = 0
    executed: list[dict[str, Any]] = []

    for entry in selected:
        target = str(entry.get("target") or "").strip()
        if not target:
            continue
        if target == "api_aggregator":
            source_ids = list(entry.get("site_ids") or [])
            result = _run_api_collection(source_ids=source_ids or None)
            executed.append(
                {
                    "target": target,
                    "source_type": "api",
                    "site_ids": source_ids,
                    "result": result,
                }
            )
            total_items += int(result.get("items", 0))
            total_errors += int(result.get("errors", 0))
            continue

        result = run_spider(target)
        executed.append(
            {
                "target": target,
                "source_type": "scrapy",
                "site_ids": list(entry.get("site_ids") or []),
                "result": result,
            }
        )
        total_items += int(result.get("items", 0))
        total_errors += int(result.get("errors", 0))

    return {
        "status": "success" if total_errors == 0 else "partial",
        "count": total_items,
        "errors": total_errors,
        "executed_count": len(executed),
        "executed": executed,
    }


async def _airflow_api_request(
    method: str, path: str, payload: Optional[dict] = None,
) -> dict:
    """Proxy simple vers l'API REST Airflow."""
    url = f"{AIRFLOW_URL}{path}"
    try:
        async with httpx.AsyncClient(
            timeout=AIRFLOW_API_TIMEOUT,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        ) as client:
            response = await client.request(method=method, url=url, json=payload)
    except Exception as err:
        logger.warning(f"Airflow indisponible ({url}): {err}")
        raise HTTPException(
            status_code=503,
            detail=f"Airflow indisponible: {err}",
        ) from err

    if response.status_code >= 300:
        detail = response.text[:500]
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Airflow API {response.status_code}: {detail}",
        )

    try:
        return response.json()
    except Exception:
        return {"raw": response.text}


def _run_api_collection(source_ids: Optional[List[str]] = None) -> dict:
    """
    Execute la collecte API sur tout le registre (ou un sous-ensemble de source_ids).
    """
    started = time.time()
    run_id = f"api_collect_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    try:
        from api_sourcing.collector import run_api_collection
        count = run_api_collection(source_ids=source_ids)
        duration_seconds = round(time.time() - started, 3)
        _safe_append_api_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "success",
            "items": count,
            "errors": 0,
            "duration_seconds": duration_seconds,
            "timeout_seconds": None,
            "qa": {},
            "fingerprint": {},
            "source_ids": list(source_ids or []),
        })
        logger.info(f"Collecte API terminee: {count} offres")
        return {"items": count, "errors": 0}
    except ImportError:
        logger.warning("Module api_sourcing non disponible")
        duration_seconds = round(time.time() - started, 3)
        _safe_append_api_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "skipped",
            "items": 0,
            "errors": 1,
            "duration_seconds": duration_seconds,
            "timeout_seconds": None,
            "qa": {},
            "fingerprint": {},
            "note": "module_unavailable",
            "source_ids": list(source_ids or []),
        })
        return {"items": 0, "errors": 1}
    except Exception as err:
        logger.error(f"Erreur collecte API: {err}")
        duration_seconds = round(time.time() - started, 3)
        _safe_append_api_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "error",
            "items": 0,
            "errors": 1,
            "duration_seconds": duration_seconds,
            "timeout_seconds": None,
            "qa": {},
            "fingerprint": {},
            "exception": str(err),
            "source_ids": list(source_ids or []),
        })
        return {"items": 0, "errors": 1}


def _safe_append_api_report(report: dict) -> None:
    try:
        append_scrape_report(report)
    except Exception as err:
        logger.warning(f"Rapport API non enregistre: {err}")


def _parse_priority_ref(priority_ref: str) -> int:
    value = (priority_ref or "").strip().lower()
    aliases = {
        "1": PRIORITY_HIGH,
        "high": PRIORITY_HIGH,
        "haute": PRIORITY_HIGH,
        "haut": PRIORITY_HIGH,
        "2": PRIORITY_MEDIUM,
        "medium": PRIORITY_MEDIUM,
        "moyenne": PRIORITY_MEDIUM,
        "moyen": PRIORITY_MEDIUM,
        "3": PRIORITY_LOW,
        "low": PRIORITY_LOW,
        "basse": PRIORITY_LOW,
        "bas": PRIORITY_LOW,
        "4": PRIORITY_NIGHTLY,
        "nightly": PRIORITY_NIGHTLY,
        "nuit": PRIORITY_NIGHTLY,
        "nocturne": PRIORITY_NIGHTLY,
    }
    priority = aliases.get(value)
    if priority is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Priorite invalide. Utiliser 1..4 ou "
                "high|medium|low|nightly"
            ),
        )
    return priority


def _resolve_targets(targets: List[str]) -> tuple[List[str], List[str]]:
    """
    Convertit une liste heterogene (site_id, spider, api_aggregator) en:
    - spiders dedies a executer
    - sources API a collecter
    """
    spider_sites = get_spider_sites()
    api_sites = get_api_sites()

    spider_targets = set()
    api_sources = set()

    for target in targets:
        if target in SPIDERS:
            spider_targets.add(target)
            continue

        if target == "api_aggregator":
            api_sources.update(api_sites.keys())
            continue

        site_info = SITES_REGISTRY.get(target)
        if not site_info:
            continue

        if site_info.get("source") == "api" and target in api_sites:
            api_sources.add(target)
            continue

        spider_name = site_info.get("spider")
        if target in spider_sites and spider_name in SPIDERS:
            spider_targets.add(spider_name)

    return sorted(spider_targets), sorted(api_sources)


def _has_dedicated_folder(info: dict) -> bool:
    """
    Indique si la source est branchee sur un composant dedie:
    - scraping: spider dedie
    - api: provider dedie dans api_sourcing/sources/<provider>
    """
    if info.get("source") == "api":
        return bool(info.get("api_provider"))
    return bool(info.get("spider"))

# Utilitaires
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
