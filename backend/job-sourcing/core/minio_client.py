# Client MinIO pour le stockage des donnees brutes (Bronze)
# Gere l'upload des offres d'emploi vers MinIO

import json
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from loguru import logger
from minio import Minio
from minio.error import S3Error

from core.config_loader import ConfigLoader


class MinioStorageClient:
    """
    Client pour interagir avec MinIO.
    Gere le stockage des donnees brutes des offres d'emploi.
    """

    def __init__(self):
        """
        Initialise le client MinIO avec les parametres de configuration.
        """
        config = ConfigLoader().get_config()
        minio_config = config.get("storage", {}).get("minio", {})

        self.endpoint = os.getenv("MINIO_ENDPOINT", minio_config.get("endpoint"))
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "")
        self.bucket_name = os.getenv("MINIO_BUCKET_RAW", minio_config.get("bucket_raw", "talentflow-bronze"))
        self.secure = minio_config.get("secure", False)

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        self._ensure_bucket_exists()
        logger.info(f"Client MinIO initialise: {self.endpoint}")

    def _ensure_bucket_exists(self) -> None:
        """
        Verifie que le bucket existe, sinon le cree.
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket cree: {self.bucket_name}")
        except S3Error as err:
            logger.error(f"Erreur lors de la creation du bucket: {err}")
            raise

    def _generate_object_name(self, site_name: str, job_hash: str) -> str:
        """
        Genere un nom d'objet unique pour le stockage.
        
        Args:
            site_name: Nom du site source
            job_hash: Hash unique de l'offre
        
        Returns:
            Nom de l'objet au format site/date/hash.json
        """
        date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        return f"{site_name}/{date_prefix}/{job_hash}.json"

    def list_buckets(self) -> list:
        """Liste les buckets disponibles."""
        return self.client.list_buckets()

    def list_objects(self, prefix: str = "") -> list:
        """Liste les objets dans le bucket courant (recursif)."""
        return list(self.client.list_objects(
            self.bucket_name, prefix=prefix, recursive=True
        ))

    def upload_job(self, site_name: str, job_data: dict) -> bool:
        """
        Upload une offre d'emploi vers MinIO.
        
        Args:
            site_name: Nom du site source
            job_data: Donnees de l'offre a stocker
        
        Returns:
            True si l'upload a reussi, False sinon
        """
        try:
            job_hash = job_data.get("hash", "unknown")
            object_name = self._generate_object_name(site_name, job_hash)

            # Conversion en JSON
            json_data = json.dumps(job_data, ensure_ascii=False, indent=2)
            data_bytes = json_data.encode("utf-8")
            data_stream = BytesIO(data_bytes)

            # Upload vers MinIO
            self.client.put_object(
                self.bucket_name,
                object_name,
                data_stream,
                length=len(data_bytes),
                content_type="application/json"
            )

            logger.debug(f"Offre uploadee: {object_name}")
            return True

        except S3Error as err:
            logger.error(f"Erreur lors de l'upload: {err}")
            return False

    def list_jobs(self, site_name: Optional[str] = None) -> list:
        """
        Liste les offres stockees dans MinIO.
        
        Args:
            site_name: Filtre par site (optionnel)
        
        Returns:
            Liste des objets trouves
        """
        prefix = f"{site_name}/" if site_name else ""
        objects = self.client.list_objects(self.bucket_name, prefix=prefix)
        return [obj.object_name for obj in objects]

    def clear_bucket(self) -> dict:
        """
        Vide completement le bucket bronze (supprime tous les objets).
        Utilise pour reinitialiser le data lake avant un nouveau crawl.

        Returns:
            {"deleted": n, "errors": m}
        """
        deleted = 0
        errors = 0
        try:
            objects = self.client.list_objects(
                self.bucket_name, recursive=True,
            )
            for obj in objects:
                try:
                    self.client.remove_object(self.bucket_name, obj.object_name)
                    deleted += 1
                except S3Error as err:
                    logger.error(f"Erreur suppression {obj.object_name}: {err}")
                    errors += 1
            logger.info(
                f"Bucket {self.bucket_name} vide: {deleted} supprimes, "
                f"{errors} erreurs"
            )
        except S3Error as err:
            logger.error(f"Erreur vidage bucket: {err}")
            errors += 1
        return {"deleted": deleted, "errors": errors}

    def count_objects(self, prefix: str = "") -> int:
        """Compte le nombre total d'objets dans le bucket."""
        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True,
            )
            return sum(1 for _ in objects)
        except S3Error:
            return 0
