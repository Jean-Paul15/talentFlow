# Post-processeur pour le pipeline de nettoyage
# Gere l'archivage des fichiers traites dans MinIO

import os
from typing import Dict, List

from loguru import logger
from minio import Minio
from minio.commonconfig import CopySource

from .config_loader import ConfigLoader


class PostProcessor:
    """
    Post-traitement des objets MinIO apres nettoyage.
    Deplace ou marque les fichiers traites.
    """

    def __init__(self):
        config = ConfigLoader().get_config()
        minio_cfg = config.get("storage", {}).get("minio", {})

        self.client = Minio(
            os.getenv("MINIO_ENDPOINT", minio_cfg.get("endpoint", "minio:9000")),
            access_key=os.getenv("MINIO_ACCESS_KEY", minio_cfg.get("access_key", "")),
            secret_key=os.getenv("MINIO_SECRET_KEY", minio_cfg.get("secret_key", "")),
            secure=minio_cfg.get("secure", False),
        )
        self.source_bucket = os.getenv("MINIO_BUCKET_RAW", minio_cfg.get("bucket_raw", "talentflow-bronze"))
        self.archive_bucket = "talentflow-archive"
        # Zero-loss policy by default: keep Bronze objects unless explicitly enabled.
        self.delete_after_archive = os.getenv("DELETE_BRONZE_AFTER_ARCHIVE", "false").strip().lower() in {"1", "true", "yes", "on"}
        self._ensure_archive_bucket()

    def _ensure_archive_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.archive_bucket):
                self.client.make_bucket(self.archive_bucket)
        except Exception as err:
            logger.warning(f"Archive bucket check: {err}")

    def process_completed(self, object_names: List[str]) -> Dict[str, int]:
        """Marque les objets comme traites (copie vers archive)."""
        archived = 0
        deleted = 0
        errors = 0
        for name in object_names:
            try:
                self.client.copy_object(
                    self.archive_bucket,
                    name,
                    CopySource(self.source_bucket, name),
                )
                archived += 1
                if self.delete_after_archive:
                    self.client.remove_object(self.source_bucket, name)
                    deleted += 1
            except Exception as err:
                logger.debug(f"Archivage ignore pour {name}: {err}")
                errors += 1
        return {
            "archived": archived,
            "deleted_from_bronze": deleted,
            "errors": errors,
            "delete_after_archive": self.delete_after_archive,
        }
