# Producteur Kafka pour l'ingestion des offres d'emploi.
# Publie les evenements "raw jobs" qui seront consommes par Spark Streaming.

import json
import os
from typing import Any, Dict, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError
from loguru import logger


def _parse_bootstrap_servers(raw_value: str) -> list[str]:
    """Convertit la variable d'env en liste d'endpoints Kafka."""
    return [entry.strip() for entry in raw_value.split(",") if entry.strip()]


class KafkaJobProducer:
    """
    Producteur Kafka pour les offres d'emploi brutes.
    """

    def __init__(self):
        bootstrap_env = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.bootstrap_servers = _parse_bootstrap_servers(bootstrap_env)
        self.topic = os.getenv("KAFKA_TOPIC_JOBS_RAW", "talentflow_jobs_raw")
        self.enabled = os.getenv("KAFKA_ENABLED", "true").lower() == "true"

        self._producer: Optional[KafkaProducer] = None
        if self.enabled:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda payload: json.dumps(
                        payload,
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    key_serializer=lambda key: key.encode("utf-8"),
                    acks="all",
                    retries=5,
                    linger_ms=20,
                    max_in_flight_requests_per_connection=1,
                )
                logger.info(
                    f"Kafka producer initialise: topic={self.topic}, "
                    f"brokers={self.bootstrap_servers}"
                )
            except Exception as err:
                logger.error(f"Kafka init failed: {err}")
                self._producer = None
        else:
            logger.warning("Kafka desactive (KAFKA_ENABLED=false)")

    def is_ready(self) -> bool:
        """Indique si la publication Kafka est active."""
        return self._producer is not None

    def send_job(self, site_name: str, job_data: Dict[str, Any]) -> bool:
        """
        Publie un evenement job brut sur Kafka.
        """
        if not self._producer:
            return False

        event = dict(job_data)
        event["source_site"] = site_name
        event["event_type"] = "job_scraped"
        event["event_version"] = "1.0.0"

        event_key = (
            event.get("fingerprint")
            or event.get("hash")
            or event.get("source_url")
            or "unknown"
        )

        try:
            future = self._producer.send(
                self.topic,
                key=event_key,
                value=event,
            )
            future.get(timeout=10)
            return True
        except KafkaError as err:
            logger.error(f"Kafka publish failed ({self.topic}): {err}")
            return False
        except Exception as err:
            logger.error(f"Kafka publish unexpected error: {err}")
            return False

    def flush(self) -> None:
        if self._producer:
            self._producer.flush(timeout=10)

    def close(self) -> None:
        if self._producer:
            self._producer.flush(timeout=10)
            self._producer.close(timeout=10)
