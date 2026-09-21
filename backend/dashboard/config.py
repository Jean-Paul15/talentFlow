# Configuration centrale du dashboard TalentFlow
# Variables d'environnement et parametres globaux

import os
from dotenv import load_dotenv

load_dotenv()

# -- Elasticsearch ---
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", 9200))
ES_INDEX = os.getenv("ES_INDEX", "talentflow_jobs")

# -- Redis ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# -- MinIO ---
MINIO_HOST = os.getenv("MINIO_HOST", "localhost:9000")
MINIO_USER = os.getenv("MINIO_ROOT_USER", "")
MINIO_PASS = os.getenv("MINIO_ROOT_PASSWORD", "")

# -- Services API ---
JOB_SOURCING_URL = os.getenv("JOB_SOURCING_URL", "http://localhost:8000")
DATA_CLEANING_URL = os.getenv("DATA_CLEANING_URL", "http://localhost:8002")
SEARCH_ENGINE_URL = os.getenv("SEARCH_ENGINE_URL", "http://localhost:8003")
RECOMMENDATION_URL = os.getenv("RECOMMENDATION_URL", "http://localhost:8001")
LAKE_API_URL = os.getenv("LAKE_API_URL", "http://localhost:8004")

# -- Airflow ---
AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8080")

# -- Dashboard Mode ---
# full = toutes les pages
# sourcing_only = uniquement collecte -> kafka/spark -> stockage -> api
# lake_only = uniquement minio -> lake api -> dashboard
DASHBOARD_MODE = os.getenv("DASHBOARD_MODE", "full").strip().lower()
