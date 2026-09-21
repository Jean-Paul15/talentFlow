# Indexeur MongoDB -> Qdrant
# Synchronise les offres avec vectorisation dense (full ou delta)

from __future__ import annotations

import os
import uuid
from typing import Dict, List

from loguru import logger

from core.config_loader import ConfigLoader
from core.mongo_reader import MongoReader
from services.embedding_service import EmbeddingService
from services.document_builder import (
    get_text_for_embedding,
    is_probable_job_document,
    prepare_qdrant_payload,
    build_canonical_job_identity,
)
from services.qdrant_index_manager import QdrantIndexManager


class QdrantJobIndexer:
    """
    Indexe les offres MongoDB dans Qdrant avec embeddings.
    """

    def __init__(self):
        self.mongo = MongoReader()
        self.embedding_service = EmbeddingService()

        # Derive vector size from embedding model if possible.
        vector_size = self._infer_vector_size()
        self.index_manager = QdrantIndexManager(vector_size=vector_size)
        self.client = self.index_manager.client

        config = ConfigLoader().get_config()
        emb_config = config.get("embeddings", {})
        self.batch_size = int(emb_config.get("batch_size", 32))
        self.collection_name = self.index_manager.collection_name
        self.enable_sparse = self.index_manager.enable_sparse
        self.sparse_model_name = os.getenv("QDRANT_SPARSE_MODEL", "Qdrant/bm25")
        self._sparse_encoder = None
        self._sparse_load_attempted = False
        self.incremental_enabled = str(
            os.getenv("SEARCH_INDEX_INCREMENTAL_ENABLED", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}

    def index_all(self, reindex: bool = False) -> Dict[str, int]:
        if self.client is None:
            raise RuntimeError("Qdrant client indisponible")
        if not self.index_manager.collection_exists():
            self.index_manager.create_collection(force=False)
        elif reindex:
            self.index_manager.create_collection(force=True)

        incremental = bool(self.incremental_enabled and not reindex)
        stats = {
            "indexed": 0,
            "errors": 0,
            "candidates": 0,
            "mode": "incremental" if incremental else "full",
            "marked": 0,
            "skipped_non_job": 0,
        }
        batch: List[dict] = []

        if incremental:
            job_stream = self.mongo.stream_jobs_delta("qdrant", self.batch_size)
            try:
                stats["candidates"] = int(self.mongo.count_jobs_delta("qdrant"))
            except Exception as err:
                logger.warning(f"Count delta Qdrant indisponible, poursuite sans compteur: {err}")
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

        logger.info(f"Indexation Qdrant terminee: {stats}")
        return stats

    def _index_batch(self, jobs: List[dict]) -> Dict[str, int]:
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
            stats["marked"] += self.mongo.bulk_mark_indexed_backend("qdrant", skipped_jobs)
        if not indexable_jobs:
            return stats

        texts = [get_text_for_embedding(job) for job in indexable_jobs]
        embeddings = self.embedding_service.embed(texts)
        if embeddings is None:
            logger.error("Embeddings indisponibles pour batch Qdrant")
            stats["errors"] = len(indexable_jobs)
            return stats

        try:
            points = self._build_points(indexable_jobs, embeddings, texts)
            self._upsert_points(points)
            stats["indexed"] = len(points)
            stats["marked"] += self.mongo.bulk_mark_indexed_backend("qdrant", indexable_jobs)
        except Exception as err:
            logger.error(f"Qdrant batch upsert error: {err}")
            stats["errors"] = len(indexable_jobs)

        return stats

    def _build_points(self, jobs: List[dict], embeddings, texts: List[str]) -> List[object]:
        try:
            from qdrant_client.http import models as qm  # type: ignore
        except Exception as err:
            raise RuntimeError(f"qdrant-client models indisponibles: {err}") from err

        points = []
        sparse_vectors = self._build_sparse_vectors(texts)
        for idx, (job, embedding) in enumerate(zip(jobs, embeddings)):
            payload = prepare_qdrant_payload(job)
            point_id = self._qdrant_point_id(job)
            dense_vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            sparse = sparse_vectors[idx] if idx < len(sparse_vectors) else None
            vector_value = dense_vector
            if self.enable_sparse:
                vector_value = {"dense": dense_vector}
            if sparse is not None and self.enable_sparse:
                # Qdrant's Python docs support sparse vectors as raw objects under
                # the named vector key. This is more robust across client versions
                # than mixing dense lists and qm.SparseVector instances.
                vector_value["sparse"] = {
                    "indices": sparse["indices"],
                    "values": sparse["values"],
                }
            points.append(
                qm.PointStruct(
                    id=point_id,
                    vector=vector_value,
                    payload=payload,
                )
            )
        return points

    def _qdrant_point_id(self, job: dict) -> str:
        """
        Qdrant n'accepte que uint ou UUID comme point id.
        On génère un UUID déterministe à partir de l'identite canonique de l'offre
        (semantic_fingerprint/url canonique/fallback), afin de dedup cross-sources.
        """
        identity = build_canonical_job_identity(job)
        if not identity:
            return str(uuid.uuid4())
        try:
            # Keep valid UUIDs as-is.
            return str(uuid.UUID(identity))
        except Exception:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"talentflow-job:{identity}"))

    def _upsert_points(self, points: List[object]) -> None:
        if not points:
            return
        # Newer qdrant-client
        if hasattr(self.client, "upsert"):
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points,
            )
            return
        # Legacy fallback (unlikely)
        if hasattr(self.client, "upload_points"):  # pragma: no cover
            self.client.upload_points(self.collection_name, points=points)
            return
        raise RuntimeError("Aucune methode d'upsert Qdrant supportee")

    def _infer_vector_size(self) -> int:
        # Optional env override is already handled by manager. This is a best effort.
        try:
            probe = self.embedding_service.embed_single("dimension probe")
            if probe:
                return len(probe)
        except Exception as err:
            logger.warning(f"Inference dimension embedding impossible: {err}")
        return 384

    def _get_sparse_encoder(self):
        if not self.enable_sparse:
            return None
        if self._sparse_load_attempted:
            return self._sparse_encoder
        self._sparse_load_attempted = True
        try:
            from fastembed import SparseTextEmbedding  # type: ignore

            self._sparse_encoder = SparseTextEmbedding(model_name=self.sparse_model_name)
        except Exception as err:
            logger.warning(f"SparseTextEmbedding indisponible ({self.sparse_model_name}), dense-only: {err}")
            self._sparse_encoder = None
        return self._sparse_encoder

    def _build_sparse_vectors(self, texts: List[str]) -> List[dict]:
        encoder = self._get_sparse_encoder()
        if encoder is None:
            return []
        try:
            sparse_list = list(encoder.embed(texts))
            out: List[dict] = []
            for sparse in sparse_list:
                raw_indices = getattr(sparse, "indices", None)
                raw_values = getattr(sparse, "values", None)
                if hasattr(raw_indices, "tolist"):
                    raw_indices = raw_indices.tolist()
                if hasattr(raw_values, "tolist"):
                    raw_values = raw_values.tolist()
                indices = list(raw_indices) if raw_indices is not None else []
                values = list(raw_values) if raw_values is not None else []
                if len(indices) > 0 and len(values) > 0:
                    out.append({"indices": indices, "values": values})
                else:
                    out.append(None)
            return out
        except Exception as err:
            logger.warning(f"Embedding sparse Qdrant impossible, dense-only: {err}")
            return []
