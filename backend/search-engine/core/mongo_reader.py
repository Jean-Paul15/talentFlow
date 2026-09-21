# Client MongoDB pour lire les offres enrichies

import os
from datetime import datetime, timezone
from typing import Generator, Iterable, Optional

from pymongo import MongoClient, UpdateOne
from loguru import logger

from core.config_loader import ConfigLoader


class MongoReader:
    """
    Lit les offres depuis MongoDB (source Silver).
    """
    _instance = None
    _client: MongoClient = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self) -> None:
        """
        Connexion a MongoDB.
        """
        config = ConfigLoader().get_config()
        mongo_config = config.get("mongodb", {})
        
        uri = os.getenv(
            "MONGODB_URI",
            os.getenv(
                "MONGO_URI",
                str(mongo_config.get("uri", "mongodb://localhost:27017")),
            ),
        )
        database = os.getenv(
            "MONGODB_DATABASE",
            os.getenv("MONGO_DATABASE", str(mongo_config.get("database", "talentflow"))),
        )
        collection = os.getenv(
            "MONGODB_COLLECTION",
            os.getenv("MONGO_COLLECTION", str(mongo_config.get("collection", "jobs"))),
        )
        
        self._client = MongoClient(uri)
        self._db = self._client[database]
        self._collection = self._db[collection]
        
        logger.info(f"MongoDB connecte: {database}.{collection}")
    
    def count_jobs(self, query: Optional[dict] = None) -> int:
        """
        Compte les offres.
        """
        return self._collection.count_documents(query or {})
    
    def stream_jobs(
        self,
        batch_size: int = 100,
        query: Optional[dict] = None,
        sort: Optional[list] = None,
    ) -> Generator[dict, None, None]:
        """
        Stream les offres par batch.
        """
        cursor = self._collection.find(query or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.batch_size(batch_size)
        
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            yield doc
    
    def get_unindexed(self, batch_size: int = 100) -> Generator[dict, None, None]:
        """
        Retourne les offres non encore indexees dans ES.
        """
        query = {"indexed_in_es": {"$ne": True}}
        return self.stream_jobs(batch_size, query)

    def get_backend_delta_query(self, backend: str) -> dict:
        """
        Query incremental pour un backend d'indexation (es/qdrant/...).
        Reindexe les nouveaux docs et ceux dont processed_at a change.
        """
        key = self._normalize_backend_key(backend)
        flag_field = f"indexed_in_{key}"
        processed_marker_field = f"{key}_indexed_processed_at"
        # $expr permet de comparer le processed_at courant et le marqueur d'indexation.
        return {
            "$or": [
                {flag_field: {"$ne": True}},
                {processed_marker_field: {"$exists": False}},
                {"$expr": {"$ne": [f"${processed_marker_field}", "$processed_at"]}},
            ]
        }

    def count_jobs_delta(self, backend: str) -> int:
        """Compte les documents a reindexer pour un backend donne."""
        return self.count_jobs(self.get_backend_delta_query(backend))

    def stream_jobs_delta(
        self,
        backend: str,
        batch_size: int = 100,
    ) -> Generator[dict, None, None]:
        """
        Stream incremental (delta-only) pour un backend.
        Trie par processed_at pour un comportement stable.
        """
        query = self.get_backend_delta_query(backend)
        return self.stream_jobs(
            batch_size=batch_size,
            query=query,
            sort=[("processed_at", 1), ("_id", 1)],
        )

    def mark_indexed_backend(
        self,
        backend: str,
        job_id: str,
        *,
        processed_at: Optional[str] = None,
        indexed_at: Optional[str] = None,
    ) -> None:
        """
        Marque une offre comme indexee pour un backend (compat ES/Qdrant).
        """
        self.bulk_mark_indexed_backend(
            backend,
            [{"_id": job_id, "processed_at": processed_at}],
            indexed_at=indexed_at,
        )

    def bulk_mark_indexed_backend(
        self,
        backend: str,
        jobs: Iterable[dict],
        *,
        indexed_at: Optional[str] = None,
    ) -> int:
        """
        Marque un batch de jobs comme indexes dans Mongo (source Silver).
        Retourne le nombre de docs modifies.
        """
        from bson import ObjectId

        key = self._normalize_backend_key(backend)
        flag_field = f"indexed_in_{key}"
        processed_marker_field = f"{key}_indexed_processed_at"
        indexed_at_field = f"{key}_indexed_at"

        ts = indexed_at or datetime.now(timezone.utc).isoformat()
        ops = []
        for job in jobs:
            job_id = str(job.get("_id") or "").strip()
            if not job_id:
                continue
            set_payload = {
                flag_field: True,
                indexed_at_field: ts,
            }
            processed_at = job.get("processed_at")
            if processed_at:
                set_payload[processed_marker_field] = processed_at
            ops.append(
                UpdateOne(
                    {"_id": ObjectId(job_id)},
                    {"$set": set_payload},
                )
            )
        if not ops:
            return 0
        result = self._collection.bulk_write(ops, ordered=False)
        return int(getattr(result, "modified_count", 0) or 0)
    
    def mark_indexed(self, job_id: str) -> None:
        """
        Marque une offre comme indexee.
        """
        # Compat historique: equivalent ES sans marqueur de processed_at.
        self.mark_indexed_backend("es", job_id)

    @staticmethod
    def _normalize_backend_key(backend: str) -> str:
        value = (backend or "").strip().lower()
        if value in {"elasticsearch", "es"}:
            return "es"
        return value or "search"
