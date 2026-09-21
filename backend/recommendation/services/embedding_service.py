from __future__ import annotations

import os
from threading import RLock
from typing import List

from loguru import logger

try:
    from fastembed import TextEmbedding
except Exception:  # pragma: no cover
    TextEmbedding = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


class EmbeddingService:
    """
    Local embedding service for recommendation.
    Priorité runtime:
    - fastembed (léger, sans torch)
    - fallback sentence-transformers seulement si présent
    """

    def __init__(self):
        self.model_name = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        self.device = str(os.getenv("EMBEDDING_DEVICE", "cpu")).strip() or "cpu"
        self.model = None
        self.backend = None
        self._load_model()

    def _load_model(self) -> None:
        if TextEmbedding is not None:
            try:
                logger.info(f"Chargement embedding recommendation fastembed: {self.model_name}")
                cache_dir = str(os.getenv("FASTEMBED_CACHE_DIR", "/opt/fastembed-cache")).strip() or "/opt/fastembed-cache"
                self.model = TextEmbedding(model_name=self.model_name, cache_dir=cache_dir)
                self.backend = "fastembed"
                logger.info("✓ Embedding recommendation charge via fastembed")
                return
            except Exception as err:
                logger.warning(f"Embedding recommendation fastembed indisponible: {err}")

        if SentenceTransformer is not None:
            try:
                logger.info(
                    f"Chargement embedding recommendation sentence-transformers: {self.model_name} ({self.device})"
                )
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.backend = "sentence-transformers"
                logger.info("✓ Embedding recommendation charge via sentence-transformers")
                return
            except Exception as err:
                logger.warning(f"Embedding recommendation sentence-transformers indisponible: {err}")

        logger.warning("Recommendation embeddings indisponibles: aucun backend charge")

    def embed_single(self, text: str) -> List[float] | None:
        if self.model is None:
            return None
        try:
            if self.backend == "fastembed":
                vectors = list(self.model.embed([str(text or "")]))
                if not vectors:
                    return None
                vector = vectors[0]
                return vector.tolist() if hasattr(vector, "tolist") else list(vector)

            vector = self.model.encode(str(text or ""), show_progress_bar=False)
            return vector.tolist() if hasattr(vector, "tolist") else list(vector)
        except Exception as err:
            logger.warning(f"Embedding recommendation failed: {err}")
            return None


_service: EmbeddingService | None = None
_lock = RLock()


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is not None:
        return _service
    with _lock:
        if _service is None:
            _service = EmbeddingService()
    return _service
