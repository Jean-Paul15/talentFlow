# Client Elasticsearch
# Gestion de la connexion et des opérations principales

import os

# Compat NumPy 2.x pour certaines versions du client elasticsearch-py
# qui référencent encore np.float_/np.int_ au runtime.
try:  # pragma: no cover - dépend de l'image/runtime
    import numpy as _np  # type: ignore

    if not hasattr(_np, "float_") and hasattr(_np, "float64"):
        _np.float_ = _np.float64  # type: ignore[attr-defined]
    if not hasattr(_np, "int_") and hasattr(_np, "int64"):
        _np.int_ = _np.int64  # type: ignore[attr-defined]
    if not hasattr(_np, "complex_") and hasattr(_np, "complex128"):
        _np.complex_ = _np.complex128  # type: ignore[attr-defined]
except Exception:
    pass

from elasticsearch import Elasticsearch
from core.config_loader import ConfigLoader


class ElasticsearchClient:
    """
    Client singleton pour Elasticsearch.
    Gère la connexion et les opérations de base.
    """
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialise la connexion Elasticsearch."""
        config = ConfigLoader().get_config()
        es_config = config.get("elasticsearch", {})
        
        es_host = os.getenv(
            "ELASTICSEARCH_HOST",
            os.getenv("ES_HOST", str(es_config.get("host", "localhost"))),
        )
        es_port = os.getenv(
            "ELASTICSEARCH_PORT",
            os.getenv("ES_PORT", str(es_config.get("port", 9200))),
        )
        es_user = os.getenv("ELASTICSEARCH_USER", es_config.get("user"))
        es_password = os.getenv("ELASTICSEARCH_PASSWORD", es_config.get("password"))
        
        # Construire l'URL
        es_url = f"http://{es_host}:{es_port}"
        
        try:
            kwargs = {}
            if es_user and es_password:
                kwargs["basic_auth"] = (es_user, es_password)
            self._client = Elasticsearch([es_url], **kwargs)
            # Vérifier la connexion
            if self._client.ping():
                print(f"✓ Elasticsearch connecté à {es_url}")
            else:
                print(f"✗ Impossible de se connecter à {es_url}")
        except Exception as e:
            print(f"✗ Erreur connexion Elasticsearch: {e}")
            self._client = None
    
    def get_client(self) -> Elasticsearch:
        """Retourne le client Elasticsearch."""
        if self._client is None:
            self._initialize()
        return self._client
    
    def health(self) -> dict:
        """Retourne le statut de santé du cluster."""
        if self._client is None:
            return {"status": "disconnected"}
        try:
            return self._client.cluster.health()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def index_exists(self, index_name: str) -> bool:
        """Vérifie si un index existe."""
        if self._client is None:
            return False
        try:
            return self._client.indices.exists(index=index_name)
        except Exception as e:
            print(f"✗ Erreur lors de la vérification de l'index: {e}")
            return False
    
    def create_index(self, index_name: str, mappings: dict) -> bool:
        """Crée un nouvel index avec les mappings."""
        if self._client is None:
            print("✗ Client Elasticsearch non connecté")
            return False
        
        try:
            if self.index_exists(index_name):
                print(f"ℹ Index {index_name} existe déjà")
                return True
            
            self._client.indices.create(
                index=index_name,
                mappings=mappings
            )
            print(f"✓ Index {index_name} créé avec succès")
            return True
        except Exception as e:
            print(f"✗ Erreur création index: {e}")
            return False
