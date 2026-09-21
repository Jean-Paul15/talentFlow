# Integration API Gateway - Ajoute orchestration
from fastapi import FastAPI
from .orchestration.service_router import router as orchestration_router
from .orchestration.health_monitor import ServiceHealthMonitor
from .orchestration.service_orchestrator import ServiceOrchestrator

async def setup_orchestration(app: FastAPI):
    """Configure orchestration au demarrage"""
    
    orchestrator = ServiceOrchestrator()
    health_monitor = ServiceHealthMonitor(orchestrator)
    
    # Routes
    app.include_router(orchestration_router)
    
    @app.on_event("startup")
    async def startup_orchestration():
        await health_monitor.start()
    
    @app.on_event("shutdown")
    async def shutdown_orchestration():
        await health_monitor.stop()
        # Stop all services
        for container in orchestrator.running_services.values():
            try:
                container.stop()
            except:
                pass
