from collections import defaultdict
from datetime import datetime
import os
from urllib.parse import urlparse

from loguru import logger
from scrapy.exceptions import DropItem

from core.job_normalizer import (
    compute_job_fingerprint,
    compute_job_semantic_fingerprint,
    normalize_job_record,
)
from core.redis_client import RedisFingerprint
from core.kafka_producer import KafkaJobProducer


class DataQualityNormalizationPipeline:
    """
    Normalise les champs critiques (date, candidature, aliases) pour tous les spiders.
    """

    def open_spider(self, spider):
        self.drop_non_job = str(
            os.getenv("SCRAPY_DROP_NON_JOB_ITEMS", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.stats = {
            "total": 0,
            "rejected_non_job": 0,
            "posted_date_iso": 0,
            "deadline_iso": 0,
            "apply_url": 0,
            "apply_email": 0,
            "apply_phone": 0,
            "apply_method_known": 0,
            "description_ok": 0,
            "expired": 0,
        }

    def process_item(self, item, spider):
        normalize_job_record(item, source_name=getattr(spider, "name", ""))
        self.stats["total"] += 1
        if self.drop_non_job and item.get("is_probable_job") is False:
            self.stats["rejected_non_job"] += 1
            raise DropItem("Non-offre probable (filtre qualité)")
        if item.get("posted_date_iso"):
            self.stats["posted_date_iso"] += 1
        if item.get("deadline_iso"):
            self.stats["deadline_iso"] += 1
        if item.get("apply_url"):
            self.stats["apply_url"] += 1
        if item.get("apply_email"):
            self.stats["apply_email"] += 1
        if item.get("apply_phone"):
            self.stats["apply_phone"] += 1
        if item.get("apply_method") and item.get("apply_method") != "unknown":
            self.stats["apply_method_known"] += 1
        if len((item.get("description") or "").strip()) >= 120:
            self.stats["description_ok"] += 1
        if item.get("is_expired") is True:
            self.stats["expired"] += 1
        return item

    def close_spider(self, spider):
        total = max(self.stats["total"], 1)
        logger.info(
            f"DataQuality[{spider.name}]: total={self.stats['total']} "
            f"rejected_non_job={self.stats['rejected_non_job']} "
            f"date_iso={self.stats['posted_date_iso']} "
            f"({(self.stats['posted_date_iso'] / total) * 100:.1f}%) "
            f"deadline_iso={self.stats['deadline_iso']} "
            f"({(self.stats['deadline_iso'] / total) * 100:.1f}%) "
            f"apply_method={self.stats['apply_method_known']} "
            f"({(self.stats['apply_method_known'] / total) * 100:.1f}%) "
            f"description_ok={self.stats['description_ok']} "
            f"({(self.stats['description_ok'] / total) * 100:.1f}%) "
            f"apply_url={self.stats['apply_url']} "
            f"apply_email={self.stats['apply_email']} "
            f"apply_phone={self.stats['apply_phone']} "
            f"expired={self.stats['expired']}"
        )


class FingerprintPipeline:
    """
    Pipeline anti-duplication avec Redis.
    Utilise SHA256 sur url+titre+description.
    """

    def open_spider(self, spider):
        self.redis_client = RedisFingerprint()
        self.semantic_dedup_enabled = str(
            os.getenv("SCRAPY_SEMANTIC_DEDUP_ENABLED", "true")
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.stats = {"duplicates": 0, "semantic_duplicates": 0, "new": 0}

    def process_item(self, item, spider):
        fingerprint = self._calculate_hash(item)
        semantic_fingerprint = item.get("semantic_fingerprint")
        if not semantic_fingerprint and self.semantic_dedup_enabled:
            semantic_fingerprint = compute_job_semantic_fingerprint(item)
            if semantic_fingerprint:
                item["semantic_fingerprint"] = semantic_fingerprint

        if self.redis_client.exists(fingerprint):
            self.stats["duplicates"] += 1
            raise DropItem(f"Doublon: {fingerprint}")
        if self.semantic_dedup_enabled and semantic_fingerprint:
            if self.redis_client.exists_prefixed("fingerprint_semantic", semantic_fingerprint):
                self.stats["semantic_duplicates"] += 1
                raise DropItem(f"Doublon semantique: {semantic_fingerprint}")

        self.redis_client.add(fingerprint, {"url": item.get("source_url", "")})
        if self.semantic_dedup_enabled and semantic_fingerprint:
            self.redis_client.add_prefixed(
                "fingerprint_semantic",
                semantic_fingerprint,
                {
                    "url": item.get("source_url", ""),
                    "title": item.get("title", ""),
                },
            )
        item["fingerprint"] = fingerprint
        item["scraped_at"] = datetime.now().isoformat()
        self.stats["new"] += 1
        return item

    def _calculate_hash(self, item) -> str:
        return compute_job_fingerprint(item)

    def close_spider(self, spider):
        logger.info(f"Fingerprint: {self.stats}")


class KafkaPipeline:
    """
    Pipeline d'ingestion Kafka.
    Ventile par source reelle (domaine) au lieu du nom du spider.
    """

    def open_spider(self, spider):
        self.kafka_producer = KafkaJobProducer()
        self.produced = 0
        self.errors = 0
        self.per_site = defaultdict(int)

    def process_item(self, item, spider):
        job_dict = dict(item)
        fingerprint = item.get("fingerprint", "unknown")
        job_dict["hash"] = fingerprint

        # Ventiler par source reelle pour le deep_crawler
        if spider.name == "deep_crawler":
            site_name = self._extract_site_key(item)
        else:
            site_name = spider.name

        job_dict["storage_prefix"] = site_name

        success = self.kafka_producer.send_job(site_name, job_dict)
        if success:
            self.produced += 1
            self.per_site[site_name] += 1
            logger.info(f"[Kafka:{site_name}] {item.get('title', '?')}")
        else:
            self.errors += 1
            logger.error(f"Echec publication Kafka: {item.get('title', '?')}")
            raise DropItem("Publication Kafka impossible")

        return item

    def _extract_site_key(self, item) -> str:
        """Extrait une cle de site depuis source_url ou source_name."""
        source_name = item.get("source_name", "")
        if source_name and source_name != "deep_crawler":
            # Nettoyer le domaine : www.emploi.tg -> emploi_tg
            key = source_name.replace("www.", "")
            key = key.split(".")[0] if "." in key else key
            return key.replace("-", "_").replace(" ", "_")

        url = item.get("source_url", "")
        if url:
            domain = urlparse(url).netloc.replace("www.", "")
            key = domain.split(".")[0] if "." in domain else domain
            return key.replace("-", "_").replace(" ", "_")

        return "deep_crawler"

    def close_spider(self, spider):
        self.kafka_producer.flush()
        self.kafka_producer.close()
        logger.info(
            f"Kafka: {self.produced} publies, {self.errors} erreurs"
        )
        if self.per_site:
            for site, count in sorted(
                self.per_site.items(), key=lambda x: -x[1]
            ):
                logger.info(f"  {site}: {count}")
