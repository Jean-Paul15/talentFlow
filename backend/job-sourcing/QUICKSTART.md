# Guide Demarrage Rapide - Etape 1 TalentFlow

## Installation (5 minutes)

### Pre-requis
```bash
- Docker Desktop installe
- Docker Compose 3.8+
- Python 3.11+
- 4 GB RAM disponible
```

### Etape 1 : Cloner et configurer
```bash
cd talentFlow/backend/job-sourcing

# Copier variables environnement
cp .env.example .env

# Installer dependances Python (local)
pip install -r requirements.txt
```

### Etape 2 : Demarrer infrastructure
```bash
# Demarrer tous les services
docker-compose up -d

# Verifier status
docker-compose ps

# Services attendus :
# - talentflow-minio (ports 9000, 9001)
# - talentflow-redis (port 6379)
# - talentflow-postgres (port 5432)
# - talentflow-airflow-webserver (port 8080)
# - talentflow-airflow-scheduler
```

### Etape 3 : Premiere execution
```bash
# Test spider specifique
python manage.py run anpe_togo

# Resultat attendu :
# [INFO] Spider anpe_togo initialise
# [INFO] Liens offres trouves: 50
# [INFO] Scraping termine: {'stored': 45, 'duplicates': 5}
```

## Interfaces disponibles

### MinIO Console (Stockage Bronze)
```
URL      : http://localhost:9001
User     : <a définir dans .env>
Password : <a définir dans .env>

Navigation :
→ Buckets → raw-data → anpe_togo → 2025-01-20 → {hash}.json
```

### Airflow Web UI (Orchestration)
```
URL      : http://localhost:8080
User     : admin
Password : admin

Navigation :
→ DAGs → job_sourcing_togo_main → Activer (toggle)
→ Trigger DAG manuellement (bouton play)
```

### Redis CLI (Fingerprints)
```bash
docker exec -it talentflow-redis redis-cli

# Commandes utiles :
KEYS talentflow:fingerprint:*
DBSIZE
INFO memory
```

## Tests validation

### Test 1 : Services actifs
```bash
# MinIO health check
curl http://localhost:9000/minio/health/live

# Redis ping
docker exec talentflow-redis redis-cli ping
# Reponse attendue : PONG

# Airflow health
curl http://localhost:8080/health
```

### Test 2 : Validation complete
```bash
python validate_etape1.py

# Resultat attendu :
# PASS - docker_services
# PASS - redis_connectivity
# PASS - minio_connectivity
# PASS - airflow_connectivity
# SCORE: 4/4 tests valides
```

### Test 3 : Scraping complet
```bash
# Executer tous les spiders actifs
python manage.py run all

# Verifier MinIO
# → Console MinIO → Buckets → raw-data
# → Doit contenir dossiers : anpe_togo, emploi_tg, emploitogo_com, miabejob

# Verifier Redis
docker exec talentflow-redis redis-cli DBSIZE
# Doit retourner nombre > 0
```

## Troubleshooting

### Probleme : Services ne demarrent pas
```bash
# Verifier logs
docker-compose logs minio
docker-compose logs redis
docker-compose logs airflow-webserver

# Reset complet
docker-compose down -v
docker-compose up -d
```

### Probleme : Spider erreur connexion MinIO
```bash
# Verifier variables environnement
cat .env

# Tester connexion MinIO
python -c "from core.minio_client import MinioStorageClient; c=MinioStorageClient(); print('OK')"
```

### Probleme : Redis fingerprint erreur
```bash
# Verifier Redis actif
docker exec talentflow-redis redis-cli ping

# Test connexion
python -c "from core.redis_client import RedisFingerprint; r=RedisFingerprint(); print(r.get_stats())"
```

### Probleme : Airflow DAG non visible
```bash
# Verifier DAG file
ls -la airflow/dags/job_sourcing_dag.py

# Restart scheduler
docker-compose restart airflow-scheduler

# Verifier logs
docker-compose logs airflow-scheduler | grep "DAG"
```

## Monitoring production

### Logs scraping
```bash
# Logs temps reel
tail -f logs/scraping_$(date +%Y-%m-%d).log

# Erreurs uniquement
tail -f logs/errors_$(date +%Y-%m-%d).log
```

### Stats Redis
```bash
docker exec talentflow-redis redis-cli INFO stats
docker exec talentflow-redis redis-cli MEMORY USAGE talentflow:fingerprint:example
```

### Usage MinIO
```bash
# Via Console MinIO
http://localhost:9001 → Monitoring → Metrics

# Espace utilise
docker exec talentflow-minio du -sh /data
```

## Arret services

### Arret propre
```bash
docker-compose stop
```

### Arret avec nettoyage volumes
```bash
# ATTENTION : Supprime toutes les donnees
docker-compose down -v
```

### Arret selectif
```bash
# Arreter uniquement spiders
docker-compose stop scraper

# Redemarrer
docker-compose start scraper
```

## Prochaines actions

1. **Activer DAGs Airflow**
   - Ouvrir http://localhost:8080
   - Toggle ON pour `job_sourcing_togo_main`
   - Toggle ON pour `job_sourcing_togo_secondary`

2. **Configurer alertes**
   - Ajouter email dans airflow/dags/job_sourcing_dag.py
   - Variable `email_on_failure: True`

3. **Ajuster frequences**
   - Modifier cron dans DAG selon besoins
   - Actuel : 6h et 18h (main), 12h (secondary)

4. **Passer Etape 2 : Data Cleaning**
   - Service FastAPI enrichissement
   - Validation Pydantic
   - Stockage MongoDB (Silver)

---

**Questions ?** Consulter [ETAPE_1_COMPLETE.md](docs/ETAPE_1_COMPLETE.md)
