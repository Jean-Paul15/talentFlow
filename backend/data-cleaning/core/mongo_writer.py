# Ecrivain MongoDB pour le service de nettoyage
# Stocke les donnees nettoyees (Silver) dans MongoDB

from __future__ import annotations

import os
from typing import Dict, List

from loguru import logger
from pymongo import MongoClient, UpdateOne

from .config_loader import ConfigLoader


class MongoWriter:
    """
    Ecrit les offres nettoyees dans MongoDB (couche Silver).
    Dedup prioritaire sur URL source (plus fiable), puis fallback semantique.
    """

    def __init__(self):
        config = ConfigLoader().get_config()
        mongo_cfg = config.get("mongodb", {})

        uri = os.getenv("MONGODB_URI", mongo_cfg.get("uri", "mongodb://mongodb:27017/talentflow_silver"))
        db_name = mongo_cfg.get("database", "talentflow_silver")
        collection = mongo_cfg.get("collection", "jobs")

        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection]
        logger.info(f"MongoWriter initialise: {db_name}.{collection}")

    def _merge_filter(self, job: dict) -> dict:
        source_url = (job.get("source_url") or "").strip()
        dedup_hash = (job.get("dedup_hash") or "").strip()
        semfp = (job.get("semantic_fingerprint") or "").strip()

        # Regle principale: si URL presente, on fusionne uniquement par URL.
        if source_url:
            return {"source_url": source_url}

        # Sinon fallback semantique/hashes.
        clauses = []
        if dedup_hash:
            clauses.append({"dedup_hash": dedup_hash})
        if semfp:
            clauses.append({"semantic_fingerprint": semfp})

        if not clauses:
            # Dernier recours (faible qualite): source_name + title + company
            return {
                "source_name": job.get("source_name"),
                "title": job.get("title"),
                "company": job.get("company"),
            }
        if len(clauses) == 1:
            return clauses[0]
        return {"$or": clauses}

    def bulk_upsert(self, jobs: List[dict]) -> Dict[str, int]:
        """Insere ou met a jour un batch d'offres."""
        if not jobs:
            return {"inserted": 0, "modified": 0}

        operations = []
        for job in jobs:
            filter_key = self._merge_filter(job)
            operations.append(UpdateOne(filter_key, {"$set": job}, upsert=True))

        try:
            result = self.collection.bulk_write(operations, ordered=False)
            stats = {
                "inserted": result.upserted_count,
                "modified": result.modified_count,
            }
            logger.info(f"Bulk upsert: {stats}")
            return stats
        except Exception as err:
            logger.error(f"Erreur bulk upsert: {err}")
            return {"inserted": 0, "modified": 0}

    def count(self) -> int:
        """Nombre total de documents."""
        return self.collection.count_documents({})

    def count_jobs(self) -> int:
        """Alias pour compatibilite avec main.py."""
        return self.count()

    def insert_job(self, job: dict) -> None:
        """Insere ou met a jour une offre individuelle."""
        filter_key = self._merge_filter(job)
        self.collection.update_one(filter_key, {"$set": job}, upsert=True)
