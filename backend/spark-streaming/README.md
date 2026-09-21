# Spark Streaming Ingestion

Job Spark Structured Streaming qui:
- consomme le topic Kafka `KAFKA_TOPIC_JOBS_RAW`
- ecrit les messages en JSON dans MinIO Bronze (`MINIO_BUCKET_RAW`)
- maintient un checkpoint (`SPARK_CHECKPOINT_PATH`) pour reprise

## Variables utiles

- `KAFKA_BOOTSTRAP_SERVERS` (defaut: `kafka:9092`)
- `KAFKA_TOPIC_JOBS_RAW` (defaut: `talentflow_jobs_raw`)
- `MINIO_ENDPOINT` (defaut: `minio:9000`)
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET_RAW` (defaut: `talentflow-bronze`)
- `SPARK_TRIGGER_SECONDS` (defaut: `15`)
- `SPARK_CHECKPOINT_PATH` (defaut: `/tmp/spark-checkpoints/jobs-raw-to-minio`)
