# Retry Logic avec Circuit Breaker
import logging
import asyncio
from functools import wraps
from typing import Callable, TypeVar, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """États circuit breaker"""
    CLOSED = "closed"      # Normal
    OPEN = "open"         # Coupé (trop d'erreurs)
    HALF_OPEN = "half_open"  # Test récupération


class CircuitBreaker:
    """Circuit breaker pour LLM calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        reset_timeout: int = 120
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    def record_success(self):
        """Enregistre succès"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Enregistre échec"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit OUVERT: {self.failure_count} échecs"
            )
    
    def can_attempt(self) -> bool:
        """Peut-on tenter un appel?"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).seconds
                if elapsed > self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit DEMI-OUVERT: test récupération")
                    return True
            return False
        
        return True


circuit_breaker = CircuitBreaker()


def with_retry(
    max_attempts: int = 3,
    timeout: float = 30.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator retry avec timeout et backoff exponentiel
    
    Args:
        max_attempts: Nombre max de tentatives
        timeout: Timeout par tentative (secondes)
        backoff_factor: Multiplicateur délai entre tentatives
        exceptions: Tuple des exceptions à retry
        
    Example:
        @with_retry(max_attempts=3, timeout=30)
        async def call_llm(...):
            return await llm.ainvoke(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not circuit_breaker.can_attempt():
                raise Exception("Circuit breaker OUVERT: service indisponible")
            
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(
                        f"Tentative {attempt}/{max_attempts}: {func.__name__}"
                    )
                    
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                    
                    circuit_breaker.record_success()
                    
                    if attempt > 1:
                        logger.info(
                            f"Succès après {attempt} tentatives: {func.__name__}"
                        )
                    
                    return result
                    
                except asyncio.TimeoutError:
                    last_exception = TimeoutError(
                        f"Timeout après {timeout}s: {func.__name__}"
                    )
                    logger.warning(f"Timeout tentative {attempt}: {func.__name__}")
                    
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Erreur tentative {attempt}: {func.__name__} - {str(e)}"
                    )
                
                if attempt < max_attempts:
                    delay = backoff_factor ** (attempt - 1)
                    logger.info(f"Retry dans {delay}s...")
                    await asyncio.sleep(delay)
            
            circuit_breaker.record_failure()
            logger.error(
                f"Échec après {max_attempts} tentatives: {func.__name__}"
            )
            raise last_exception
        
        return wrapper
    return decorator
