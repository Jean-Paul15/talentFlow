# Unified Redis Factory - UNIQUE redis client pour tout le backend
import redis
from typing import Optional
import logging
from .config import get_redis_config

logger = logging.getLogger(__name__)

class RedisFactory:
    """Redis singleton - lazy initialization"""
    
    _instance: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    @classmethod
    def get_pool(cls) -> redis.ConnectionPool:
        """Get connection pool (reuse connections)"""
        if cls._instance is None:
            config = get_redis_config()
            
            cls._instance = redis.ConnectionPool(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                db=config.get("db", 0),
                max_connections=config.get("max_connections", 20),
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL  
                    3: 3   # TCP_KEEPCNT
                }
            )
            logger.info("Redis pool initialized")
        
        return cls._instance
    
    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get redis client"""
        if cls._client is None:
            cls._client = redis.Redis(connection_pool=cls.get_pool())
        
        return cls._client
    
    @classmethod
    def close(cls):
        """Close all connections"""
        if cls._instance:
            cls._instance.disconnect()
            cls._instance = None
            cls._client = None
            logger.info("Redis pool closed")

# Convenience function
def get_redis() -> redis.Redis:
    """Get redis client - use this everywhere"""
    return RedisFactory.get_client()
