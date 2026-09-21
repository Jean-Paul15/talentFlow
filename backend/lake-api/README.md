# Lake API (FastAPI)

Service FastAPI pour interroger la couche Bronze dans MinIO.

## Endpoints

- `GET /health`
- `GET /api/bronze/stats`
- `GET /api/bronze/jobs?site=...&date_prefix=YYYY-MM-DD&limit=50`
- `GET /api/bronze/jobs/all?site=...&date_prefix=YYYY-MM-DD`
- `GET /api/bronze/jobs/object/{object_name}`
- `GET /api/bronze/search?q=python&site=...&limit=20`
