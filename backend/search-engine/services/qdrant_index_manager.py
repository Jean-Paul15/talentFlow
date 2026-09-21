# Gestionnaire de collection Qdrant
# Creation, verification et stats collection vectorielle

from __future__ import annotations

import os
from typing import Optional

from loguru import logger


class QdrantIndexManager:
    """
    Gere la collection Qdrant pour les offres d'emploi.
    """

    def __init__(self, vector_size: Optional[int] = None):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY") or None
        self.collection_name = os.getenv("QDRANT_COLLECTION", "talentflow_jobs")
        self.distance = os.getenv("QDRANT_DISTANCE", "cosine").lower()
        self.vector_size = vector_size or int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
        self.enable_sparse = str(os.getenv("QDRANT_ENABLE_SPARSE", "false")).strip().lower() in {
            "1", "true", "yes", "on"
        }
        self.client = self._build_client()

    def _build_client(self):
        try:
            from qdrant_client import QdrantClient  # type: ignore
            return QdrantClient(url=self.url, api_key=self.api_key)
        except Exception as err:
            logger.error(f"Qdrant client indisponible: {err}")
            return None

    def collection_exists(self) -> bool:
        if self.client is None:
            return False
        try:
            if hasattr(self.client, "collection_exists"):
                return bool(self.client.collection_exists(self.collection_name))
        except Exception:
            pass
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False

    def create_collection(self, force: bool = False) -> bool:
        if self.client is None:
            raise RuntimeError("Qdrant client indisponible")
        if force and self.collection_exists():
            self._delete_collection()

        if self.collection_exists():
            logger.info(f"Collection Qdrant existe deja: {self.collection_name}")
            return False

        try:
            from qdrant_client.http import models as qm  # type: ignore
        except Exception as err:
            raise RuntimeError(f"qdrant-client models indisponibles: {err}") from err

        distance_map = {
            "cosine": qm.Distance.COSINE,
            "dot": qm.Distance.DOT,
            "euclid": qm.Distance.EUCLID,
            "manhattan": qm.Distance.MANHATTAN,
        }
        distance = distance_map.get(self.distance, qm.Distance.COSINE)

        vectors_config = qm.VectorParams(size=int(self.vector_size), distance=distance)

        create_kwargs = {
            "collection_name": self.collection_name,
        }
        if self.enable_sparse:
            # Named vectors: dense + sparse (BM25) when enabled.
            create_kwargs["vectors_config"] = {"dense": vectors_config}
            try:
                create_kwargs["sparse_vectors_config"] = {"sparse": qm.SparseVectorParams()}
            except Exception:
                # Some qdrant-client versions require explicit index params or don't expose SparseVectorParams.
                create_kwargs["vectors_config"] = vectors_config
        else:
            create_kwargs["vectors_config"] = vectors_config

        # Try newer and older APIs
        try:
            self.client.create_collection(**create_kwargs)
        except TypeError:
            # Older clients don't always support sparse config; fallback to dense collection.
            self.client.recreate_collection(  # pragma: no cover - older client fallback
                collection_name=self.collection_name,
                vectors_config=vectors_config,
            )
        except Exception as err:
            if self.enable_sparse:
                logger.warning(f"Creation collection sparse Qdrant echouee, fallback dense-only: {err}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=vectors_config,
                )
            else:
                raise

        logger.info(
            f"Collection Qdrant creee: {self.collection_name} "
            f"(dims={self.vector_size}, distance={self.distance}, sparse={self.enable_sparse})"
        )
        return True

    def get_doc_count(self) -> int:
        if self.client is None:
            return 0
        try:
            if hasattr(self.client, "count"):
                result = self.client.count(
                    collection_name=self.collection_name,
                    exact=True,
                )
                count = getattr(result, "count", None)
                return int(count) if count is not None else 0
        except Exception:
            pass
        try:
            info = self.client.get_collection(self.collection_name)
            count = getattr(info, "points_count", None)
            return int(count) if count is not None else 0
        except Exception:
            return 0

    def health(self) -> dict:
        ok = self.client is not None
        exists = False
        count = 0
        if ok:
            exists = self.collection_exists()
            if exists:
                count = self.get_doc_count()
        return {
            "backend": "qdrant",
            "ok": ok and exists,
            "collection_exists": exists,
            "doc_count": count,
            "collection": self.collection_name,
            "url": self.url,
        }

    def _delete_collection(self) -> None:
        if self.client is None:
            return
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.warning(f"Collection Qdrant supprimee: {self.collection_name}")
        except Exception as err:
            logger.warning(f"Suppression collection Qdrant ignoree: {err}")
