# Configuration Selector - Redis vs In-Memory
import os
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state_manager import AnalysisStateManager
    from .redis_state_manager import RedisStateManager

logger = logging.getLogger(__name__)


def get_state_manager():
    """Factory pour sélectionner state manager
    
    En dev: In-memory (rapide, simple)
    En prod: Redis (scalable, persistent)
    
    Env var: STATE_BACKEND=redis|memory
    """
    backend = os.getenv("STATE_BACKEND", "memory").lower()
    
    if backend == "redis":
        logger.info("State Manager: REDIS (production)")
        from .redis_state_manager import redis_state_manager
        return redis_state_manager
    else:
        logger.info("State Manager: IN-MEMORY (dev)")
        from .state_manager import analysis_state_manager
        return analysis_state_manager


# Export singleton
state_backend = get_state_manager()
