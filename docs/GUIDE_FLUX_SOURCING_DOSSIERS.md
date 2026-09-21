# TalentFlow - Guide Flux et Dossiers (Sourcing)

## Objectif
Ce document sert de carte de navigation pour presenter le projet sans se perdre dans le code.
Il explique:
- le flux de donnees de bout en bout,
- les modes d'execution (local vs serveur),
- le role de chaque dossier important,
- la logique de synchronisation MinIO.

---

## 1) Modes d'execution

### Mode `all` (local)
Usage: travail complet (collecte + traitements + recherche + UI).

Contient notamment:
- collecte: `job-sourcing`
- ingestion: `kafka`, `spark-streaming`
- stockage: `minio`
- exposition: `lake-api`, autres APIs
- visualisation: `streamlit`

### Mode `sourcing-only` (local)
Usage: demonstration pipeline collecte -> stockage.

Contient:
- `job-sourcing`
- `kafka`, `zookeeper`
- `spark-streaming`
- `minio`
- `lake-api`
- `streamlit`
- `airflow` (pilotage)

### Mode `lake-only` (serveur)
Usage: demo legere et stable en production.

Contient:
- `minio`
- `lake-api`
- `streamlit`

But: afficher les donnees synchronisees depuis le local, sans charge de scraping sur la VM.

---

## 2) Flux de donnees (vision simple)

### Flux local (collecte)
1. Sources web/API -> spiders Scrapy (`job-sourcing`)
2. Deduplication Redis (fingerprint)
3. Publication Kafka (`talentflow_jobs_raw`)
4. Spark lit Kafka et ecrit en JSON dans MinIO Bronze
5. Lake API lit MinIO Bronze
6. Streamlit affiche stats, sources, exemples, recherche

### Flux serveur (presentation)
1. Sync MinIO local -> MinIO serveur (miroir strict)
2. Lake API serveur lit le bucket Bronze
3. Dashboard Streamlit serveur affiche les donnees via API

---

## 3) Synchronisation MinIO (local -> serveur)

Script principal:
- `backend/scripts/powershell/sync-minio-bronze.ps1`
- wrapper pratique: `backend/scripts/powershell/lake-only-sync.ps1`

Logique actuelle:
- miroir strict du bucket local vers le bucket serveur,
- creation/mise a jour des objets,
- suppression distante des objets supprimes en local.

Consequence:
- le serveur refletera exactement l'etat du local apres synchro.

Commande type:
```powershell
.\backend\scripts\powershell\lake-only-sync.ps1 -RemoteHost "REMOTE_HOST_IP" -Bucket "jobs-bronze"
```

---

## 4) Dossiers backend: role de chaque bloc

### `backend/job-sourcing`
Coeur de la collecte.
- API FastAPI de pilotage (`main.py`)
- execution spiders
- deduplication Redis
- publication Kafka
- registre central des sources
- orchestration settings (cron, DAG states)

### `backend/spark-streaming`
Consommateur de Kafka.
- lit les evenements jobs
- ecrit en MinIO Bronze (`site/date/hash.json`)
- checkpoint pour reprise

### `backend/lake-api`
API de lecture Bronze.
- stats globales
- liste d'objets/jobs
- recherche texte
- catalogue des sources + exemples par source

### `monitoring/`
Dashboard Streamlit.
- mode `sourcing_only`: pilotage collecte + stockage
- mode `lake_only`: dashboard API-first (serveur)

### `backend/orchestration`
DAGs Airflow et orchestration pipeline.

### `backend/data-cleaning`, `backend/search-engine`, `backend/recommendation`, `backend/api-gateway`
Blocs aval du pipeline complet (hors demo lake-only).

### `backend/scripts`
Scripts d'exploitation (deploy, sync, diagnostics, generation env).

### `backend/shared`
Composants partages entre services.

---

## 5) Focus dossier `job-sourcing` (pour ne pas se perdre)

Structure logique:

- `main.py`
  - endpoints de pilotage (`/api/scrape`, `/api/stats`, `/api/sites`, etc.)
  - proxy orchestration Airflow

- `run_spider.py` / `manage.py`
  - lancement unitaire ou multi-spiders

- `core/`
  - `sites_registry.py`: source unique de verite des sites
  - `redis_client.py`: fingerprints anti-doublons
  - `kafka_producer.py`: publication events
  - `minio_client.py`: operations bucket (purge, stats)
  - `orchestration_settings.py`: crons et activation DAGs

- `scrapy_project/`
  - `items.py`: schema item scraping
  - `middlewares.py`: comportement requetes
  - `pipelines.py`: dedup + envoi Kafka
  - `settings.py`: config Scrapy
  - `spiders/`: un dossier par site

- `scrapy_project/spiders/<site>/`
  - `spider.py`: navigation/pagination
  - `parser.py`: extraction/metiers
  - `selectors.py`: selecteurs CSS/XPath
  - `config.yml`: parametres site

- `api_sourcing/`
  - collecte des providers API (JSearch, Adzuna, RemoteOK, etc.)
  - publication Kafka avec meme logique de fingerprint

- `airflow/dags/`
  - DAGs de pilotage collecte

- `tests/`, `data/`, `logs/`, `tmp/`
  - qualite, jeux de donnees, traces, temporaire

---

## 6) Scenario d'execution recommande (presentation)

### Etape A - Local (production des donnees)
1. lancer `sourcing-only` local
2. executer scraping
3. verifier que MinIO local contient des objets Bronze

### Etape B - Sync vers serveur
1. lancer `lake-only-sync.ps1`
2. verifier `total_objects` via Lake API serveur

### Etape C - Demo serveur
1. ouvrir Streamlit serveur
2. montrer KPIs, repartition par source, exemples, endpoints API

---

## 7) Endpoints utiles a presenter

### Job Sourcing API (local)
- `/health`
- `/api/scrape`
- `/api/stats`
- `/api/sites`
- `/api/schedule`

### Lake API (serveur ou local)
- `/health`
- `/api/bronze/stats`
- `/api/bronze/jobs`
- `/api/bronze/search`
- `/api/bronze/sources`
- `/api/bronze/sources/{site}/examples`
- `/docs`

---

## 8) Messages cles pour la soutenance

- Separation claire entre collecte (local) et presentation (serveur).
- Deduplication a l'ingestion (fingerprint Redis) + idempotence objet (`hash.json`).
- Exposition API propre pour lecture des donnees Bronze.
- Dashboard base sur API (pas de dependance forte au runtime scraping en serveur).
- Synchronisation maitrisee local -> serveur pour une demo fiable.

