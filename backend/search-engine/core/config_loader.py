# Chargeur de configuration
# Lit settings.yml avec substitution de variables d'environnement

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

# Charger .env
load_dotenv()


def _substitute_env_vars(value: str) -> str:
    """
    Remplace ${VAR:default} par la valeur d'environnement.
    """
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    
    def replacer(match):
        var_name = match.group(1)
        default = match.group(2) or ""
        return os.getenv(var_name, default)
    
    return re.sub(pattern, replacer, value)


def _process_config(config: Any) -> Any:
    """
    Traite recursivement la config pour substituer les variables.
    """
    if isinstance(config, dict):
        return {k: _process_config(v) for k, v in config.items()}
    if isinstance(config, list):
        return [_process_config(item) for item in config]
    if isinstance(config, str):
        return _substitute_env_vars(config)
    return config


class ConfigLoader:
    """
    Charge la configuration depuis settings.yml.
    """
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_config(self) -> Dict[str, Any]:
        """
        Retourne la configuration chargee.
        """
        if self._config is None:
            self._load_config()
        return self._config
    
    def _load_config(self) -> None:
        """
        Charge le fichier YAML.
        """
        config_path = Path(__file__).parent.parent / "config" / "settings.yml"

        if not config_path.exists():
            # Fallback env-first: permettre au service de démarrer sans settings.yml
            self._config = {}
            return

        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        self._config = _process_config(raw_config)
