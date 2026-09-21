# Pipeline Big Data (Kafka + Spark + MinIO + Airflow)

## Flux cible

1. `job-sourcing` scrape les sites/APIs
2. `job-sourcing` publie chaque offre sur Kafka (`talentflow_jobs_raw`)
3. `spark-streaming` consomme Kafka en continu
4. `spark-streaming` ecrit les objets JSON dans MinIO Bronze
5. `data-cleaning` lit Bronze et alimente Silver (Mongo/ES)
6. `airflow` orchestre le cycle complet via `talentflow_pipeline`

## Services ajoutes / modifies

- Kafka + Zookeeper dans `backend/docker-compose.yml`
- Producteur Kafka Scrapy dans `backend/job-sourcing/scrapy_project/pipelines.py`
- Job Spark streaming dans `backend/spark-streaming/stream_to_minio.py`
- API FastAPI Lake pour interrogation Bronze dans `backend/lake-api/main.py`
- DAG Airflow unifie dans `backend/orchestration/dags/talentflow_pipeline.py`

## Endpoints utiles

- `POST /api/scrape` (`job-sourcing`) -> publie vers Kafka
- `GET /api/stats` (`job-sourcing`) -> redis/kafka/bronze stats
- `GET /api/bronze/stats` (`lake-api`) -> volume Bronze
- `GET /api/bronze/jobs` (`lake-api`) -> liste objets Bronze
- `GET /api/bronze/search` (`lake-api`) -> recherche texte simple
