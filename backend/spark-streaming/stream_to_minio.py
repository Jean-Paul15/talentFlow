"""
Spark Structured Streaming:
- lit les evenements jobs depuis Kafka
- ecrit les donnees brutes en objets JSON dans MinIO (Bronze)

Le job est idempotent: la cle objet est basee sur le fingerprint/hash.
"""

import json
import os
from datetime import datetime
from io import BytesIO
from typing import Dict

from loguru import logger
from minio import Minio
from minio.error import S3Error
from pyspark.sql import DataFrame, SparkSession


def build_spark() -> SparkSession:
    app_name = os.getenv("SPARK_APP_NAME", "talentflow-kafka-to-minio")
    return (
        SparkSession.builder
        .appName(app_name)
        .getOrCreate()
    )


def create_minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "")
    secret_key = os.getenv("MINIO_SECRET_KEY", "")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )

    bucket = os.getenv("MINIO_BUCKET_RAW", "talentflow-bronze")
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"Bucket MinIO cree: {bucket}")
    return client


def _safe_site_name(payload: Dict) -> str:
    source_site = payload.get("source_site")
    if source_site:
        return str(source_site).replace(" ", "_").replace("-", "_")

    source_name = payload.get("source_name")
    if source_name:
        return str(source_name).replace(" ", "_").replace("-", "_")

    return "unknown_site"


def _safe_job_id(payload: Dict) -> str:
    return (
        str(payload.get("hash"))
        if payload.get("hash")
        else str(payload.get("fingerprint", "unknown"))
    )


def _extract_date(payload: Dict) -> str:
    raw_ts = payload.get("scraped_at")
    if not raw_ts:
        return datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # format attendu isoformat()
        normalized = str(raw_ts).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%d")
    except ValueError:
        return datetime.utcnow().strftime("%Y-%m-%d")


def write_batch_to_minio(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.isEmpty():
        logger.info(f"Batch {batch_id}: vide")
        return

    minio_client = create_minio_client()
    bucket = os.getenv("MINIO_BUCKET_RAW", "talentflow-bronze")

    written = 0
    errors = 0

    for row in batch_df.toLocalIterator():
        try:
            payload = json.loads(row.json_payload)
            payload["kafka_partition"] = row.kafka_partition
            payload["kafka_offset"] = row.kafka_offset
            payload["kafka_timestamp"] = (
                row.kafka_timestamp.isoformat()
                if row.kafka_timestamp
                else None
            )

            site = _safe_site_name(payload)
            job_id = _safe_job_id(payload)
            event_date = _extract_date(payload)
            object_name = f"{site}/{event_date}/{job_id}.json"

            raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            minio_client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=BytesIO(raw),
                length=len(raw),
                content_type="application/json",
            )
            written += 1
        except (json.JSONDecodeError, S3Error, Exception) as err:
            errors += 1
            logger.error(f"Batch {batch_id}: write error - {err}")

    logger.info(
        f"Batch {batch_id}: {written} objets ecrits, {errors} erreurs"
    )


def main() -> None:
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.getenv("KAFKA_TOPIC_JOBS_RAW", "talentflow_jobs_raw")
    starting_offsets = os.getenv("SPARK_STARTING_OFFSETS", "latest")
    trigger_seconds = int(os.getenv("SPARK_TRIGGER_SECONDS", "15"))
    checkpoint = os.getenv(
        "SPARK_CHECKPOINT_PATH",
        "/tmp/spark-checkpoints/jobs-raw-to-minio",
    )

    logger.info(
        f"Spark stream start: topic={topic}, brokers={bootstrap_servers}, "
        f"checkpoint={checkpoint}"
    )

    stream_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", starting_offsets)
        .option("failOnDataLoss", "false")
        .load()
        .selectExpr(
            "CAST(value AS STRING) AS json_payload",
            "partition AS kafka_partition",
            "offset AS kafka_offset",
            "timestamp AS kafka_timestamp",
        )
    )

    query = (
        stream_df.writeStream
        .foreachBatch(write_batch_to_minio)
        .option("checkpointLocation", checkpoint)
        .trigger(processingTime=f"{trigger_seconds} seconds")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
