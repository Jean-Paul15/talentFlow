# Unified Config Loader - Centralise toutes les configurations
import yaml
import os
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Charge configs YAML uniformément"""
    
    CONFIG_DIR = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config"
    )
    
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def load(cls, filename: str) -> Dict[str, Any]:
        """Charge et cache fichier config"""
        if filename in cls._cache:
            return cls._cache[filename]
        
        path = os.path.join(cls.CONFIG_DIR, filename)
        
        if not os.path.exists(path):
            logger.warning(f"Config file not found: {path}")
            return {}
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            cls._cache[filename] = data
            return data
    
    @classmethod
    def get(cls, filename: str, key: str, default: Any = None) -> Any:
        """Get nested config value"""
        config = cls.load(filename)
        
        for part in key.split('.'):
            if isinstance(config, dict):
                config = config.get(part)
            else:
                return default
        
        return config if config is not None else default

# Convenience shortcuts
def get_es_config() -> Dict:
    """Elasticsearch config"""
    return ConfigLoader.load("elasticsearch.yml")

def get_llm_config() -> Dict:
    """LLM config"""
    return ConfigLoader.load("llm.yml")

def get_kafka_config() -> Dict:
    """Kafka config"""
    return ConfigLoader.load("kafka.yml")

def get_redis_config() -> Dict:
    """Redis config"""
    return ConfigLoader.load("redis.yml")

def get_services_config() -> Dict:
    """Services config"""
    return ConfigLoader.load("services.yml")
