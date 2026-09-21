# Moniteur sante services - Detecte services down et relance
import asyncio
import logging
from typing import Dict
import aiohttp

logger = logging.getLogger(__name__)

class ServiceHealthMonitor:
    """Monitore sante services et relance si crash"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.check_interval = 30  # Check toutes les 30s
        self.running = False
    
    async def start(self):
        """Lance monitoring en background"""
        self.running = True
        logger.info("Health monitor started")
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Arrete monitoring"""
        self.running = False
        logger.info("Health monitor stopped")
    
    async def _monitor_loop(self):
        """Boucle monitoring continue"""
        while self.running:
            try:
                await self._check_all_services()
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Verifie sante chaque service"""
        for service_name, container in list(
            self.orchestrator.running_services.items()
        ):
            health_url = self.orchestrator.SERVICES[service_name]["health_check"]
            is_healthy = await self._check_health(health_url)
            
            if not is_healthy:
                logger.warning(f"Service {service_name} unhealthy - restarting")
                try:
                    container.restart()
                except Exception as e:
                    logger.error(f"Restart failed {service_name}: {e}")
                    # Remove from running
                    del self.orchestrator.running_services[service_name]
    
    async def _check_health(self, health_url: str) -> bool:
        """Ping health check"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=3) as resp:
                    return resp.status == 200
        except:
            return False
