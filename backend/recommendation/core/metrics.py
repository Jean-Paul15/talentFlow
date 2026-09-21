# Monitoring et Metrics (Prometheus compatible)
import logging
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
from time import time
from typing import Callable

logger = logging.getLogger(__name__)


# Compteurs
analysis_requests_total = Counter(
    'analysis_requests_total',
    'Total requêtes d\'analyse',
    ['analysis_type', 'status']
)

llm_calls_total = Counter(
    'llm_calls_total',
    'Total appels LLM',
    ['provider', 'status']
)

llm_cache_hit_total = Counter(
    "llm_cache_hit_total",
    "Total cache hits LLM",
    ["provider"],
)

llm_cache_miss_total = Counter(
    "llm_cache_miss_total",
    "Total cache misses LLM",
    ["provider"],
)

llm_reasoner_downgrade_total = Counter(
    "llm_reasoner_downgrade_total",
    "Total downgrades reasoner vers chat",
    ["reason"],
)

llm_fallback_total = Counter(
    "llm_fallback_total",
    "Total fallbacks LLM par cause",
    ["reason"],
)

circuit_breaker_trips = Counter(
    'circuit_breaker_trips_total',
    'Total circuit breaker ouvert'
)

# Histogrammes (latence)
analysis_duration_seconds = Histogram(
    'analysis_duration_seconds',
    'Durée analyses',
    ['analysis_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

llm_call_duration_seconds = Histogram(
    'llm_call_duration_seconds',
    'Durée appels LLM',
    ['provider'],
    buckets=[0.5, 1, 2, 5, 10, 30, 60]
)

# Gauges (état actuel)
active_analyses = Gauge(
    'active_analyses',
    'Analyses actives',
    ['analysis_type']
)

redis_connection_pool = Gauge(
    'redis_connection_pool_size',
    'Taille pool connexions Redis'
)

llm_queue_depth = Gauge(
    "llm_queue_depth",
    "Profondeur file attente LLM",
    ["provider"],
)

llm_budget_ratio = Gauge(
    "llm_budget_ratio",
    "Ratio d'utilisation budget LLM (0-1)",
    ["provider", "budget_kind"],
)

# Info (metadata)
app_info = Info(
    'talentflow_backend',
    'Informations application'
)


def track_analysis_metrics(analysis_type: str):
    """Decorator pour tracking metrics d'analyse
    
    Example:
        @track_analysis_metrics("gap_analysis")
        async def analyze_gaps(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            active_analyses.labels(analysis_type=analysis_type).inc()
            analysis_requests_total.labels(
                analysis_type=analysis_type,
                status='started'
            ).inc()
            
            start_time = time()
            
            try:
                result = await func(*args, **kwargs)
                
                duration = time() - start_time
                analysis_duration_seconds.labels(
                    analysis_type=analysis_type
                ).observe(duration)
                
                analysis_requests_total.labels(
                    analysis_type=analysis_type,
                    status='success'
                ).inc()
                
                logger.info(
                    f"Analyse complétée: {analysis_type} ({duration:.2f}s)"
                )
                
                return result
                
            except Exception as e:
                duration = time() - start_time
                analysis_duration_seconds.labels(
                    analysis_type=analysis_type
                ).observe(duration)
                
                analysis_requests_total.labels(
                    analysis_type=analysis_type,
                    status='error'
                ).inc()
                
                logger.error(
                    f"Analyse échouée: {analysis_type} ({duration:.2f}s) - {e}"
                )
                raise
                
            finally:
                active_analyses.labels(analysis_type=analysis_type).dec()
        
        return wrapper
    return decorator


def track_llm_call(provider: str):
    """Decorator pour tracking appels LLM
    
    Example:
        @track_llm_call("gemini")
        async def call_llm(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            llm_calls_total.labels(
                provider=provider,
                status='started'
            ).inc()
            
            start_time = time()
            
            try:
                result = await func(*args, **kwargs)
                
                duration = time() - start_time
                llm_call_duration_seconds.labels(
                    provider=provider
                ).observe(duration)
                
                llm_calls_total.labels(
                    provider=provider,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                duration = time() - start_time
                llm_call_duration_seconds.labels(
                    provider=provider
                ).observe(duration)
                
                llm_calls_total.labels(
                    provider=provider,
                    status='error'
                ).inc()
                
                logger.error(f"LLM call failed: {provider} - {e}")
                raise
        
        return wrapper
    return decorator
