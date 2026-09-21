import os
from typing import List

import numpy as np
from loguru import logger

try:
    from fastembed import TextEmbedding
except Exception:
    TextEmbedding = None

try:  # pragma: no cover
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


class EmbeddingService:
    """
    Service d'embedding pour le search-engine.

    Strategie:
    - utiliser fastembed en priorite (runtime plus leger, pas de torch)
    - fallback sentence-transformers seulement si explicitement necessaire
    """

    def __init__(self):
        self.model_name = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        self.cache_dir = os.getenv("FASTEMBED_CACHE_PATH") or None
        self.device = str(os.getenv("EMBEDDING_DEVICE", "cpu")).strip() or "cpu"
        self.backend = "none"
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        if TextEmbedding is not None:
            try:
                logger.info(f"Chargement embedding fastembed: {self.model_name}")
                self.model = TextEmbedding(
                    model_name=self.model_name,
                    cache_dir=self.cache_dir,
                    lazy_load=False,
                )
                self.backend = "fastembed"
                logger.info("✓ Modele d'embedding charge via fastembed")
                return
            except Exception as err:
                logger.warning(f"Fastembed indisponible pour {self.model_name}: {err}")

        if SentenceTransformer is not None:
            try:
                logger.info(f"Chargement embedding sentence-transformers: {self.model_name} ({self.device})")
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.backend = "sentence-transformers"
                logger.info("✓ Modele d'embedding charge via sentence-transformers")
                return
            except Exception as err:
                logger.error(f"Echec chargement sentence-transformers: {err}")

        logger.error("Aucun backend d'embedding disponible")
        self.model = None
        self.backend = "none"

    def embed(self, texts: List[str]) -> np.ndarray | None:
        if self.model is None:
            logger.error("Modele non disponible")
            return None
        try:
            normalized = [str(text or "") for text in texts]
            if self.backend == "fastembed":
                vectors = list(self.model.embed(normalized))
                return np.array(vectors, dtype=np.float32)
            embeddings = self.model.encode(normalized, show_progress_bar=False)
            return np.asarray(embeddings, dtype=np.float32)
        except Exception as err:
            logger.error(f"Erreur embedding batch: {err}")
            return None

    def embed_text(self, text: str) -> List[float] | None:
        if self.model is None:
            return None
        try:
            normalized = str(text or "")
            if self.backend == "fastembed":
                vector = list(self.model.embed([normalized]))[0]
                return vector.tolist() if hasattr(vector, "tolist") else list(vector)
            embedding = self.model.encode(normalized, show_progress_bar=False)
            return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        except Exception as err:
            logger.error(f"Erreur embedding texte: {err}")
            return None

    def embed_single(self, text: str) -> List[float] | None:
        return self.embed_text(text)
