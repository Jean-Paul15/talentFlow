# Lecteur MinIO pour le service de nettoyage
# Lit les donnees brutes (Bronze + Archive) depuis MinIO

import json
import os
from datetime import datetime
from typing import Generator, List, Optional, Tuple

from loguru import logger
from minio import Minio

from .config_loader import ConfigLoader


class MinioReader:
    """
    Lit les offres brutes depuis MinIO.
    Support multi-buckets pour retraiter Bronze + Archive sans perte.
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

        self.primary_bucket = os.getenv("MINIO_BUCKET_RAW", minio_cfg.get("bucket_raw", "jobs-bronze"))
        buckets_env = (os.getenv("MINIO_BUCKETS_RAW", "") or "").strip()
        include_archive = (os.getenv("FULL_REPROCESS_INCLUDE_ARCHIVE", "false").strip().lower() in {"1","true","yes","on"})
        if buckets_env:
            buckets = [b.strip() for b in buckets_env.split(",") if b.strip()]
        elif include_archive:
            buckets = [self.primary_bucket, "talentflow-archive"]
        else:
            buckets = [self.primary_bucket]

        # dedupe while preserving order
        seen = set()
        self.buckets: List[str] = []
        for b in buckets:
            if b not in seen:
                self.buckets.append(b)
                seen.add(b)

        self._ensure_bucket(self.primary_bucket)
        logger.info(f"MinioReader initialise: primary={self.primary_bucket} buckets={self.buckets}")

    def _ensure_bucket(self, bucket: str) -> None:
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except Exception as err:
            logger.warning(f"Bucket check ({bucket}): {err}")

    def list_new_objects(
        self,
        since_date: Optional[datetime] = None,
        site_prefix: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Liste les objets a traiter, filtre par date et site, sur tous les buckets actifs."""
        prefix = f"{site_prefix}/" if site_prefix else ""
        objects: List[Tuple[str, str]] = []
        unique_keys = set()

        for bucket in self.buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    logger.warning(f"Bucket absent, ignore: {bucket}")
                    continue
                for obj in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                    if since_date and obj.last_modified:
                        if obj.last_modified.replace(tzinfo=None) < since_date:
                            continue

                    # anti-doublon cross-bucket: meme objet logique si meme chemin
                    dedup_key = obj.object_name
                    if dedup_key in unique_keys:
                        continue
                    unique_keys.add(dedup_key)
                    objects.append((bucket, obj.object_name))
            except Exception as err:
                logger.error(f"Erreur listing MinIO bucket={bucket}: {err}")

        return objects

    def stream_objects(self, objects: List[Tuple[str, str]]) -> Generator[dict, None, None]:
        """Lit les objets JSON un par un en streaming."""
        for bucket, name in objects:
            try:
                response = self.client.get_object(bucket, name)
                data = json.loads(response.read().decode("utf-8"))
                data["_minio_object"] = name
                data["_minio_bucket"] = bucket
                yield data
            except Exception as err:
                logger.error(f"Erreur lecture {bucket}/{name}: {err}")
