# Orchestrateur services - Lance services AUTO a la demande
import docker
import logging
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import json
import sys
sys.path.insert(0, '../..')
from shared import get_redis
from shared.config import get_services_config

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """Gere cycle de vie services - auto-launch on-demand + Redis persistence"""

    def __init__(self):
        self.client = docker.from_env()
        self.running_services = {}
        self.last_used = {}
        self.redis = get_redis()
        self.config = get_services_config()
        self.SERVICES = self.config.get("services", {})
        self._load_persistent_state()

    def _load_persistent_state(self):
        """Charge etat persiste dans Redis"""
        try:
            state_key = "orchestrator:services:running"
            state = self.redis.get(state_key)
            if state:
                data = json.loads(state)
                logger.info(f"Loaded persistent state: {data}")
        except Exception as e:
            logger.warning(f"No persistent state: {e}")

    def _save_persistent_state(self):
        """Sauvegarde etat dans Redis"""
        try:
            state_key = "orchestrator:services:running"
            state = {
                "services": list(self.running_services.keys()),
                "timestamp": datetime.now().isoformat()
            }
            self.redis.setex(state_key, 3600, json.dumps(state))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def auto_launch_on_startup(self):
        """Lance services critiques au demarrage"""
        critical = self.config.get("orchestration", {}).get("auto_launch", [])
        for service_name in critical:
            logger.info(f"Auto-launching critical service: {service_name}")
            await self.get_or_launch(service_name)

    async def get_or_launch(self, service_name: str) -> bool:
        """AUTO-LAUNCH service si pas actif - transparent pour client"""
        if service_name not in self.SERVICES:
            raise ValueError(f"Service unknown: {service_name}")

        config = self.SERVICES[service_name]

        # Check si running
        if service_name in self.running_services:
            container = self.running_services[service_name]
            if container.status == "running":
                self.last_used[service_name] = datetime.now()
                return True

        # AUTO-LAUNCH (utilisateur ne fait rien)
        try:
            logger.info(f"🚀 AUTO-LAUNCHING {service_name}...")
            container = self.client.containers.run(
                config["image"],
                detach=True,
                ports={f"{config['port']}/tcp": config["port"]},
                name=f"{service_name}-on-demand",
                restart_policy={"Name": "no"}
            )

            # Attend health
            if await self._wait_healthy(service_name, config["health_check"]):
                self.running_services[service_name] = container
                self.last_used[service_name] = datetime.now()
                self._save_persistent_state()
                logger.info(f"✅ {service_name} auto-launched successfully")
                return True
            else:
                container.stop()
                return False

        except Exception as e:
            logger.error(f"Auto-launch failed {service_name}: {e}")
            return False

    async def _wait_healthy(self, service_name: str, health_url: str,
                           max_retries: int = 30) -> bool:
        """Attend health check - max 30s"""
        import aiohttp

        for i in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_url, timeout=2) as resp:
                        if resp.status == 200:
                            return True
            except:
                pass

            await asyncio.sleep(1)

        return False

    async def cleanup_idle(self):
        """Auto-stop services idle (> timeout)"""
        now = datetime.now()

        for service_name, container in list(self.running_services.items()):
            config = self.SERVICES[service_name]
            timeout = timedelta(seconds=config["timeout_seconds"])

            last_used = self.last_used.get(service_name)
            if last_used and (now - last_used) > timeout:
                try:
                    logger.info(f"⏹️ Auto-stopping idle: {service_name}")
                    container.stop()
                    del self.running_services[service_name]
                    del self.last_used[service_name]
                    self._save_persistent_state()
                except Exception as e:
                    logger.error(f"Stop error {service_name}: {e}")

    async def health(self) -> dict:
        """Status tous services"""
        return {
            "running": list(self.running_services.keys()),
            "stopped": [s for s in self.SERVICES.keys()
                       if s not in self.running_services]
        }
