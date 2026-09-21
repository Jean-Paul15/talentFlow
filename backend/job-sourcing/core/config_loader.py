# Chargeur de configuration pour le service de scraping
# Gere la lecture des fichiers YAML de configuration

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger


class ConfigLoader:
    """
    Singleton pour charger et gerer les configurations.
    Supporte les fichiers YAML et les variables d'environnement.
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Optional[dict] = None

    def __new__(cls) -> "ConfigLoader":
        """
        Implemente le pattern Singleton.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialise le chargeur de configuration.
        """
        if self._config is None:
            self._load_config()

    def _get_config_path(self) -> Path:
        """
        Determine le chemin du fichier de configuration global.
        
        Returns:
            Chemin vers le fichier global_config.yml
        """
        base_path = Path(__file__).parent.parent
        return base_path / "configs" / "global_config.yml"

    def _load_config(self) -> None:
        """
        Charge la configuration depuis le fichier YAML.
        """
        config_path = self._get_config_path()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                self._config = yaml.safe_load(file)
                logger.info(f"Configuration chargee: {config_path}")
        except FileNotFoundError:
            logger.warning(f"Fichier de configuration non trouve: {config_path}")
            self._config = {}
        except yaml.YAMLError as err:
            logger.error(f"Erreur de parsing YAML: {err}")
            self._config = {}

    def get_config(self) -> dict:
        """
        Retourne la configuration complete.
        
        Returns:
            Dictionnaire de configuration
        """
        return self._config or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Recupere une valeur de configuration par cle.
        
        Args:
            key: Cle de configuration (supporte la notation pointee)
            default: Valeur par defaut si la cle n'existe pas
        
        Returns:
            Valeur de configuration ou valeur par defaut
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def get_site_config(self, site_name: str) -> dict:
        """
        Charge la configuration specifique a un site.
        
        Args:
            site_name: Nom du site (correspond au dossier du spider)
        
        Returns:
            Configuration du site ou dictionnaire vide
        """
        base_path = Path(__file__).parent.parent
        site_config_path = base_path / "spiders" / site_name / "config.yml"

        try:
            with open(site_config_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            logger.debug(f"Pas de configuration specifique pour: {site_name}")
            return {}
        except yaml.YAMLError as err:
            logger.error(f"Erreur de parsing pour {site_name}: {err}")
            return {}

    def reload(self) -> None:
        """
        Recharge la configuration depuis le fichier.
        """
        self._config = None
        self._load_config()
