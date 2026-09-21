# Chargeur de configuration pour le service de nettoyage
# Compatible avec le ConfigLoader du job-sourcing

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger


class ConfigLoader:
    """
    Singleton pour charger et gerer les configurations.
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Optional[dict] = None

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration depuis YAML ou variables d'environnement."""
        config_path = Path(__file__).parent.parent / "configs" / "global_config.yml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
                logger.info(f"Configuration chargee: {config_path}")
        except FileNotFoundError:
            logger.warning(f"Config absente: {config_path} - utilisation env vars")
            self._config = self._config_from_env()
        except yaml.YAMLError as err:
            logger.error(f"Erreur YAML: {err}")
            self._config = self._config_from_env()

    def _config_from_env(self) -> dict:
        """Construit la configuration depuis les variables d'environnement."""
        return {
            "storage": {
                "minio": {
                    "endpoint": os.getenv("MINIO_ENDPOINT", "minio:9000"),
                    "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
                    "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
                    "bucket_raw": os.getenv("MINIO_BUCKET_RAW", "talentflow-bronze"),
                    "secure": False,
                }
            },
            "mongodb": {
                "uri": os.getenv("MONGODB_URI", "mongodb://mongodb:27017/talentflow_silver"),
                "database": os.getenv("MONGODB_DATABASE", "talentflow_silver"),
                "collection": os.getenv("MONGODB_COLLECTION", "jobs"),
            },
            "processing": {
                "batch_size": int(os.getenv("BATCH_SIZE", "50")),
            },
            "cleaning": {
                "required_fields": ["title"],
            },
            "enrichment": {
                "llm": {
                    "enabled": (
                        os.getenv("DATA_CLEANING_LLM_ENABLED", os.getenv("LLM_ENABLED", "false"))
                        .strip()
                        .lower()
                        == "true"
                    ),
                    "provider": os.getenv("DATA_CLEANING_LLM_PROVIDER", "mistral"),
                    "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
                },
                "ner": {
                    "model": os.getenv("NER_MODEL", "jjzha/jobbert_skill_extraction"),
                    "device": os.getenv("NER_DEVICE", "cpu"),
                },
            },
        }

    def get_config(self) -> dict:
        return self._config or {}

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
