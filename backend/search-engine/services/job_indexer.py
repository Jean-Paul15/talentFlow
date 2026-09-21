# Indexeur MongoDB -> Elasticsearch
# Synchronise les offres avec vectorisation (full ou delta)

import hashlib
import os
from typing import Dict, List

from loguru import logger

from core.config_loader import ConfigLoader
from core.es_client import ElasticsearchClient
from core.mongo_reader import MongoReader
from services.embedding_service import EmbeddingService
from services.index_manager import IndexManager
from services.document_builder import (
    get_text_for_embedding,
    is_probable_job_document,
    prepare_es_document,
    build_canonical_job_identity,
)


class JobIndexer:
    """
    Indexe les offres MongoDB dans Elasticsearch avec embeddings.
    """
    
    def __init__(self):
        self.es = ElasticsearchClient().get_client()
        self.mongo = MongoReader()
        self.embedding_service = EmbeddingService()
        self.index_manager = IndexManager()
        
        config = ConfigLoader().get_config()
        emb_config = config.get("embeddings", {})
        self.batch_size = emb_config.get("batch_size", 32)
        self.index_name = self.index_manager.index_name
        self.incremental_enabled = str(
            os.getenv("SEARCH_INDEX_INCREMENTAL_ENABLED", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}
    
    def index_all(self, reindex: bool = False) -> Dict[str, int]:
        """
        Indexe toutes les offres.
        """
        if not self.index_manager.index_exists():
            self.index_manager.create_index()
        elif reindex:
            self.index_manager.create_index(force=True)
        
        incremental = bool(self.incremental_enabled and not reindex)
        stats = {
            "indexed": 0,
            "errors": 0,
            "candidates": 0,
            "mode": "incremental" if incremental else "full",
            "marked": 0,
            "skipped_non_job": 0,
        }
        batch = []

        if incremental:
            job_stream = self.mongo.stream_jobs_delta("es", self.batch_size)
            try:
                stats["candidates"] = int(self.mongo.count_jobs_delta("es"))
            except Exception as err:
                logger.warning(f"Count delta ES indisponible, poursuite sans compteur: {err}")
        else:
            job_stream = self.mongo.stream_jobs(self.batch_size)

        for job in job_stream:
            batch.append(job)
            
            if len(batch) >= self.batch_size:
                result = self._index_batch(batch)
                stats["indexed"] += result["indexed"]
                stats["errors"] += result["errors"]
                stats["marked"] += result.get("marked", 0)
                stats["skipped_non_job"] += result.get("skipped_non_job", 0)
                batch = []
        
        if batch:
            result = self._index_batch(batch)
            stats["indexed"] += result["indexed"]
            stats["errors"] += result["errors"]
            stats["marked"] += result.get("marked", 0)
            stats["skipped_non_job"] += result.get("skipped_non_job", 0)
        
        self.index_manager.refresh()
        logger.info(f"Indexation terminee: {stats}")
        return stats
    
    def _index_batch(self, jobs: List[dict]) -> Dict[str, int]:
        """
        Indexe un batch d'offres avec embeddings.
        """
        stats = {"indexed": 0, "errors": 0, "marked": 0, "skipped_non_job": 0}
        if not jobs:
            return stats

        indexable_jobs = []
        skipped_jobs = []
        for job in jobs:
            if is_probable_job_document(job):
                indexable_jobs.append(job)
            else:
                skipped_jobs.append(job)
        if skipped_jobs:
            stats["skipped_non_job"] = len(skipped_jobs)
            stats["marked"] += self.mongo.bulk_mark_indexed_backend("es", skipped_jobs)
        if not indexable_jobs:
            return stats

        texts = [get_text_for_embedding(job) for job in indexable_jobs]
        embeddings = self.embedding_service.embed(texts)
        if embeddings is None:
            logger.error("Embeddings indisponibles pour batch ES")
            stats["errors"] = len(indexable_jobs)
            return stats
        
        actions = []
        for job, embedding in zip(indexable_jobs, embeddings):
            doc = prepare_es_document(job, embedding)
            actions.append({"index": {"_index": self.index_name, "_id": self._es_doc_id(job)}})
            actions.append(doc)
        
        try:
            response = self.es.bulk(operations=actions)
            if response.get("errors"):
                stats["errors"] = len(indexable_jobs)
                first_error = None
                for item in response.get("items", []) or []:
                    if not isinstance(item, dict):
                        continue
                    op_data = next(iter(item.values()), None)
                    if isinstance(op_data, dict) and op_data.get("error"):
                        first_error = op_data.get("error")
                        break
                if first_error:
                    logger.error(f"Bulk item error ES: {first_error}")
                else:
                    logger.error("Bulk ES a retourne errors=true sans detail exploitable")
            else:
                stats["indexed"] = len(indexable_jobs)
                stats["marked"] += self.mongo.bulk_mark_indexed_backend("es", indexable_jobs)
        except Exception as err:
            logger.error(f"Bulk error: {err}")
            stats["errors"] = len(indexable_jobs)
        
        return stats

    def _es_doc_id(self, job: dict) -> str:
        identity = build_canonical_job_identity(job)
        return hashlib.sha1(identity.encode("utf-8")).hexdigest()
