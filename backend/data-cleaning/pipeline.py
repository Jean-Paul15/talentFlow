# Pipeline principal de traitement
# Orchestre: Lecture Bronze -> Nettoyage -> Dedup -> Enrichissement -> MongoDB -> Post-traitement

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from core.config_loader import ConfigLoader
from core.minio_reader import MinioReader
from core.mongo_writer import MongoWriter
from core.post_processor import PostProcessor
from processors.text_cleaner import TextCleaner
from processors.deduplicator import Deduplicator
from processors.skill_enricher import SkillEnricher
from processors.quality_freshness import annotate_quality_and_freshness
from processors.source_cleaner import SourceCleaner


class CleaningPipeline:
    """
    Pipeline de nettoyage et enrichissement.
    AGNOSTIQUE DE LA SOURCE - traite tout ce qui vient de MinIO.
    """
    
    def __init__(self):
        """
        Initialise tous les composants du pipeline.
        """
        config = ConfigLoader().get_config()
        processing_config = config.get("processing", {})
        
        self.batch_size = processing_config.get("batch_size", 50)
        
        # Composants
        self.minio_reader = MinioReader()
        self.mongo_writer = MongoWriter()
        self.post_processor = PostProcessor()
        self.text_cleaner = TextCleaner()
        self.deduplicator = Deduplicator()
        self.skill_enricher = SkillEnricher()
        self.source_cleaner = SourceCleaner()
        
        # Stats
        self.stats = {"processed": 0, "skipped": 0, "errors": 0}
        # Tracking des objets traites pour post-processing
        self._processed_objects = []
        
        logger.info("CleaningPipeline initialise")
    
    def process_job(self, raw_job: dict) -> Optional[dict]:
        """
        Traite une offre individuelle.
        
        Args:
            raw_job: Offre brute depuis MinIO
        
        Returns:
            Offre nettoyee et enrichie, ou None si invalide
        """
        try:
            # 1. Validation minimale
            if not self._validate_raw(raw_job):
                self.stats["skipped"] += 1
                return None
            
            # 2. Nettoyage
            cleaned = self._clean_job(raw_job)
            
            # 3. Deduplication hash
            cleaned = self.deduplicator.add_dedup_hash(cleaned)
            
            # 4. Enrichissement IA
            enriched = self.skill_enricher.enrich_job(cleaned)

            # 4b. Signaux de fraîcheur et qualité document
            enriched = annotate_quality_and_freshness(enriched)
            
            # 5. Metadata
            enriched["processed_at"] = datetime.utcnow().isoformat()
            enriched["pipeline_version"] = "1.0.0"
            
            self.stats["processed"] += 1
            return enriched
            
        except Exception as err:
            logger.error(f"Erreur traitement: {err}")
            self.stats["errors"] += 1
            return None
    
    def _validate_raw(self, raw_job: dict) -> bool:
        """
        Valide qu'une offre brute a les champs minimaux.
        """
        config = ConfigLoader().get_config()
        required = config.get("cleaning", {}).get("required_fields", ["title"])
        
        for field in required:
            if not raw_job.get(field):
                logger.debug(f"Champ manquant: {field}")
                return False
        return True
    
    def _clean_job(self, raw_job: dict) -> dict:
        """
        Applique le nettoyage a tous les champs texte.
        """
        cleaned = {
            "title": self.text_cleaner.clean_text(raw_job.get("title")),
            "company": self.text_cleaner.clean_text(raw_job.get("company")) or "Non precise",
            "location": self.text_cleaner.normalize_location(raw_job.get("location")),
            "description": self.text_cleaner.clean_text(raw_job.get("description")),
            "contract_type": self.text_cleaner.normalize_contract_type(raw_job.get("contract_type")),
            "sector": raw_job.get("sector"),
            "salary": raw_job.get("salary"),
            "posted_date": raw_job.get("posted_date"),
            "posted_date_raw": raw_job.get("posted_date_raw"),
            "posted_date_iso": raw_job.get("posted_date_iso"),
            "deadline": raw_job.get("deadline"),
            "deadline_raw": raw_job.get("deadline_raw"),
            "deadline_iso": raw_job.get("deadline_iso"),
            "apply_url": raw_job.get("apply_url"),
            "apply_email": raw_job.get("apply_email") or raw_job.get("contact_email"),
            "apply_instructions": self.text_cleaner.clean_text(raw_job.get("apply_instructions")),
            "contact_email": raw_job.get("contact_email"),
            "contact_phone": raw_job.get("contact_phone"),
            "recruiter_name": raw_job.get("recruiter_name"),
            "source_url": raw_job.get("source_url"),
            "source_name": raw_job.get("source_name"),
            "country": self.text_cleaner.normalize_country(
                raw_job.get("country", "Togo"),
                location=raw_job.get("location"),
                source_name=raw_job.get("source_name"),
            ),
            "source_type": raw_job.get("source_type") or raw_job.get("source") or "scraping",
            "skills": raw_job.get("skills", []),
            "apply_method": raw_job.get("apply_method"),
            "days_until_deadline": raw_job.get("days_until_deadline"),
            "is_expired": raw_job.get("is_expired"),
            "is_probable_job": raw_job.get("is_probable_job", True),
            "semantic_fingerprint": raw_job.get("semantic_fingerprint"),
            "scraped_at": raw_job.get("scraped_at"),
            "extra_data": raw_job.get("extra_data") if isinstance(raw_job.get("extra_data"), dict) else {},
        }
        return self.source_cleaner.clean(cleaned, raw_job)
    
    def run(
        self,
        since_date: Optional[datetime] = None,
        site_prefix: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Execute le pipeline complet.
        
        Args:
            since_date: Ne traiter que les offres depuis cette date
            site_prefix: Filtrer par site source (optionnel)
        
        Returns:
            Statistiques d'execution
        """
        logger.info(f"Demarrage pipeline: since={since_date}, prefix={site_prefix}")
        
        # Reset stats et tracking
        self.stats = {"processed": 0, "skipped": 0, "errors": 0, "stored": 0}
        self._processed_objects = []
        
        # 1. Lister les objets a traiter
        objects = self.minio_reader.list_new_objects(since_date, site_prefix)
        logger.info(f"Objets a traiter: {len(objects)}")
        
        # 2. Traiter par batch
        batch = []
        seen_source_urls = set()
        for raw_job in self.minio_reader.stream_objects(objects):
            source_url = str(raw_job.get("source_url") or "").strip()
            if source_url:
                if source_url in seen_source_urls:
                    self.stats["skipped"] += 1
                    continue
                seen_source_urls.add(source_url)

            # Tracker l'objet MinIO source
            minio_object = raw_job.get("_minio_object")
            minio_bucket = raw_job.get("_minio_bucket")
            if minio_object and minio_bucket == self.minio_reader.primary_bucket:
                self._processed_objects.append(minio_object)

            processed = self.process_job(raw_job)
            if processed:
                batch.append(processed)

            if len(batch) >= self.batch_size:
                self._store_batch(batch)
                batch = []
        
        # 3. Stocker le dernier batch
        if batch:
            self._store_batch(batch)
        
        # 4. Post-traitement des objets Bronze (archivage/suppression)
        if self._processed_objects:
            post_result = self.post_processor.process_completed(
                self._processed_objects
            )
            self.stats["post_processing"] = post_result
            logger.info(f"Post-traitement: {post_result}")
        
        logger.info(f"Pipeline termine: {self.stats}")
        return self.stats
    
    def _store_batch(self, batch: List[dict]) -> None:
        """
        Stocke un batch dans MongoDB Silver.
        """
        result = self.mongo_writer.bulk_upsert(batch)
        self.stats["stored"] += result["inserted"] + result["modified"]
