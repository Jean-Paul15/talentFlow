# Service Router - Route requetes et lance services a la demande
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx
import logging
from .service_orchestrator import ServiceOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/services", tags=["services"])

orchestrator = ServiceOrchestrator()

SERVICE_ROUTES = {
    "analyze-cv": "recommendation",
    "match-jobs": "recommendation",
    "gap-analysis": "recommendation",
    "scrape": "job-sourcing",
    "search": "search-engine",
    "clean": "data-cleaning"
}

SERVICE_PORTS = {
    "recommendation": 8001,
    "job-sourcing": 8000,
    "search-engine": 8003,
    "data-cleaning": 8002
}

@router.post("/{endpoint}")
async def route_to_service(
    endpoint: str,
    request_data: dict,
    background_tasks: BackgroundTasks
):
    """Route requete, lance service si besoin"""
    
    # Find service
    service_name = SERVICE_ROUTES.get(endpoint)
    if not service_name:
        raise HTTPException(status_code=404, detail=f"Endpoint unknown: {endpoint}")
    
    # Launch or get service
    is_running = await orchestrator.get_or_launch(service_name)
    if not is_running:
        raise HTTPException(
            status_code=503,
            detail=f"Service {service_name} unavailable"
        )
    
    # Proxy requete
    port = SERVICE_PORTS[service_name]
    service_url = f"http://localhost:{port}/api/{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(service_url, json=request_data)
            
            # Schedule cleanup task (async)
            background_tasks.add_task(
                _schedule_cleanup_check,
                orchestrator
            )
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def services_status():
    """Status tous services"""
    return await orchestrator.health()

@router.post("/stop/{service_name}")
async def stop_service(service_name: str):
    """Arrete service manuellement"""
    if service_name not in orchestrator.running_services:
        raise HTTPException(status_code=404, detail="Service not running")
    
    try:
        container = orchestrator.running_services[service_name]
        container.stop()
        del orchestrator.running_services[service_name]
        return {"status": "stopped", "service": service_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _schedule_cleanup_check(orchestrator):
    """Check cleanup en background"""
    import asyncio
    await asyncio.sleep(30)  # Check apres 30s
    await orchestrator.cleanup_idle()
