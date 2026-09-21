# Mode Sourcing Only (sans supprimer le reste)

Objectif: montrer uniquement la chaine **collecte -> ingestion -> stockage -> API -> Streamlit**.

## Ce qui reste visible

- `job-sourcing` (Scrapy + FastAPI)
- `kafka` (bus d'evenements)
- `spark-streaming` (consumer Kafka -> MinIO Bronze)
- `minio` (stockage objets Bronze)
- `lake-api` (interrogation des donnees Bronze)
- `streamlit` (pages Sourcing, Stockage API, Flux, Architecture)

## Ce qui est cache (mais conserve)

Les services aval (`data-cleaning`, `search-engine`, `recommendation`, `api-gateway`, etc.) ne sont pas supprimes.
Ils sont juste non demarres dans ce mode.

## Lancement demo

```bash
docker compose -f backend/docker-compose.yml --profile sourcing-only up -d --build
```

Premier lancement: utiliser `--build`.
Lancements suivants (plus rapides):

```bash
docker compose -f backend/docker-compose.yml --profile sourcing-only up -d
```

Les images infra (`zookeeper`, `kafka`, `minio`, `redis`) sont en `pull_policy: if_not_present`,
donc elles ne sont pas retéléchargées à chaque démarrage.

Pour `spark-streaming`, les caches sont persistés:
- `spark_pip_cache` (pip)
- `spark_ivy_cache` (jars Spark/Kafka)

Donc les téléchargements initiaux ne se répètent pas à chaque relance.

Note: au tout premier démarrage de `spark-streaming`, le conteneur télécharge
les dépendances Python et le connecteur Kafka Spark (une seule fois).

## Arret demo

```bash
docker compose -f backend/docker-compose.yml --profile sourcing-only down
```

## Acces

- Streamlit: `http://localhost:8501`
- Sourcing API: `http://localhost:8000`
- Lake API: `http://localhost:8004`
- MinIO Console: `http://localhost:9001`

## Revenir au mode complet

1. Remettre `DASHBOARD_MODE=full` dans `backend/.env`
2. Lancer:

```bash
docker compose -f backend/docker-compose.yml --profile all up -d --build
```
