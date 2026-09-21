# Indexeur Elasticsearch pour le service de nettoyage
# Indexe les offres nettoyees (Silver) dans Elasticsearch

import os
from typing import Dict, List

from loguru import logger

from .config_loader import ConfigLoader


class ElasticsearchIndexer:
    """
    Indexe les offres nettoyees dans Elasticsearch.
    """

    INDEX_NAME = "talentflow_jobs"

    MAPPING = {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "french"},
                "company": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "location": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text", "analyzer": "french"},
                "contract_type": {"type": "keyword"},
                "sector": {"type": "keyword"},
                "salary": {"type": "text"},
                "posted_date": {"type": "text"},
                "source_url": {"type": "keyword"},
                "source_name": {"type": "keyword"},
                "country": {"type": "keyword"},
                "skills": {"type": "keyword"},
                "scraped_at": {"type": "date", "ignore_malformed": True},
                "processed_at": {"type": "date", "ignore_malformed": True},
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "french": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "french_stemmer"],
                    }
                },
                "filter": {
                    "french_stemmer": {"type": "stemmer", "language": "french"}
                },
            },
        },
    }

    def __init__(self):
        self.enabled = str(os.getenv("ES_INDEXING_ENABLED", "false")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not self.enabled:
            logger.info("ElasticsearchIndexer desactive (ES_INDEXING_ENABLED=false)")
            self.client = None
            return

        config = ConfigLoader().get_config()
        es_cfg = config.get("elasticsearch", {})

        host = os.getenv("ES_HOST", es_cfg.get("host", "elasticsearch"))
        port = int(os.getenv("ES_PORT", es_cfg.get("port", 9200)))

        try:
            from elasticsearch import Elasticsearch

            self.client = Elasticsearch([f"http://{host}:{port}"])
            self._ensure_index()
            logger.info(f"ElasticsearchIndexer initialise: {host}:{port}")
        except Exception as err:
            logger.warning(f"Elasticsearch indisponible: {err}")
            self.client = None

    def _ensure_index(self) -> None:
        """Cree l'index s'il n'existe pas."""
        if not self.client:
            return
        try:
            if not self.client.indices.exists(index=self.INDEX_NAME):
                self.client.indices.create(
                    index=self.INDEX_NAME, body=self.MAPPING
                )
                logger.info(f"Index cree: {self.INDEX_NAME}")
        except Exception as err:
            logger.error(f"Erreur creation index: {err}")

    def bulk_index(self, jobs: List[dict]) -> Dict[str, int]:
        """Indexe un batch d'offres."""
        if not self.client or not jobs:
            return {"indexed": 0, "errors": 0}

        from elasticsearch.helpers import bulk

        actions = []
        for job in jobs:
            doc_id = job.get("source_url", "")
            doc = {k: v for k, v in job.items() if not k.startswith("_")}
            actions.append({
                "_index": self.INDEX_NAME,
                "_id": doc_id,
                "_source": doc,
            })

        try:
            success, errors = bulk(self.client, actions, raise_on_error=False)
            stats = {"indexed": success, "errors": len(errors) if errors else 0}
            logger.info(f"ES bulk index: {stats}")
            return stats
        except Exception as err:
            logger.error(f"Erreur bulk index ES: {err}")
            return {"indexed": 0, "errors": len(jobs)}

    def count(self) -> int:
        """Nombre de documents dans l'index."""
        if not self.client:
            return 0
        try:
            result = self.client.count(index=self.INDEX_NAME)
            return result.get("count", 0)
        except Exception:
            return 0
