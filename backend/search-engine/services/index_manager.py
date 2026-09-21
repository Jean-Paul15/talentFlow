# Gestionnaire d'index Elasticsearch
# Creation, mise a jour et verification de l'index

import os

from loguru import logger

from core.config_loader import ConfigLoader
from core.es_client import ElasticsearchClient
from services.index_mapping import INDEX_MAPPING


class IndexManager:
    """
    Gere le cycle de vie de l'index Elasticsearch.
    """
    
    def __init__(self):
        self.es = ElasticsearchClient().get_client()
        config = ConfigLoader().get_config()
        es_config = config.get("elasticsearch", {})
        
        self.index_name = os.getenv(
            "SEARCH_INDEX_NAME",
            str(es_config.get("index_name", "talentflow_jobs")),
        )
        self.settings = es_config.get("index_settings", {})
    
    def create_index(self, force: bool = False) -> bool:
        """
        Cree l'index avec le mapping dense_vector.
        """
        if self.es.indices.exists(index=self.index_name):
            if force:
                logger.warning(f"Suppression index existant: {self.index_name}")
                self.es.indices.delete(index=self.index_name)
            else:
                logger.info(f"Index existe deja: {self.index_name}")
                return False
        
        # Fusionner settings et mapping
        body = {
            "settings": self.settings,
            **INDEX_MAPPING
        }
        
        self.es.indices.create(index=self.index_name, body=body)
        logger.info(f"Index cree: {self.index_name}")
        return True
    
    def index_exists(self) -> bool:
        """
        Verifie si l'index existe.
        """
        return self.es.indices.exists(index=self.index_name)
    
    def get_doc_count(self) -> int:
        """
        Retourne le nombre de documents indexes.
        """
        if not self.index_exists():
            return 0
        result = self.es.count(index=self.index_name)
        return result["count"]
    
    def refresh(self) -> None:
        """
        Force le rafraichissement de l'index.
        """
        self.es.indices.refresh(index=self.index_name)
