# Unified Health Check - Standard pour tous les services
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

class HealthResponse(BaseModel):
    """Standard health check response"""
    
    status: str = "ok"  # ok, degraded, error
    service: str  # api-gateway, recommendation, search-engine, etc
    version: str = "1.0.0"
    timestamp: datetime = datetime.now()
    
    dependencies: Optional[Dict[str, str]] = None  # postgres: ok, redis: ok
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "recommendation",
                "timestamp": "2026-02-02T10:30:00",
                "dependencies": {
                    "elasticsearch": "ok",
                    "redis": "ok",
                    "gemini": "ok"
                }
            }
        }

def create_health_response(service_name: str, 
                          dependencies: Dict[str, str] = None) -> HealthResponse:
    """Helper to create standard health responses"""
    return HealthResponse(
        service=service_name,
        timestamp=datetime.now(),
        dependencies=dependencies or {}
    )
