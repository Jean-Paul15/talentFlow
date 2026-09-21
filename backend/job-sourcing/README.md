# TalentFlow - Job Sourcing Service

Service de scraping Scrapy pour collecte offres d'emploi avec anti-duplication Redis et publication Kafka.

Version : 1.0.0  
Status : Fonctionnel

## Architecture

Sites Web → Scrapy Spiders → FingerprintPipeline (Redis) → KafkaPipeline → Spark Streaming → Bronze Storage (MinIO)

## Structure par site

Chaque site a son propre dossier avec separation des responsabilites :

```
scrapy_project/spiders/
├── anpe_togo/
│   ├── spider.py        (40 lignes - logique Scrapy)
│   ├── parser.py        (35 lignes - extraction donnees)
│   ├── selectors.py     (12 lignes - selecteurs CSS)
│   ├── config.yml       (config specifique)
│   └── __init__.py
├── emploi_tg/
│   ├── spider.py
│   ├── parser.py
│   ├── selectors.py
│   ├── config.yml
│   └── __init__.py
├── lucreatif/
│   ├── spider.py
│   ├── parser.py
│   ├── selectors.py
│   ├── config.yml
│   └── __init__.py
├── emploitogo_com/
│   ├── spider.py
│   ├── parser.py
│   ├── selectors.py
│   ├── config.yml
│   └── __init__.py
└── miabejob/
    ├── spider.py
    ├── parser.py
    ├── selectors.py
    ├── config.yml
    └── __init__.py
```

## Separation des responsabilites

- **spider.py** : Logique Scrapy, navigation, yield items
- **parser.py** : Extraction et parsing donnees
- **selectors.py** : Constantes CSS selectors
- **config.yml** : Config site (URL, delays, priority)

## Utilisation

```bash
# Installer
pip install -r requirements.txt

# Lancer services
docker-compose up -d

# Executer spider
scrapy crawl anpe_togo

# Ou via script
python run_spider.py anpe_togo
python run_spider.py all
```

## Interfaces

- MinIO Console: http://localhost:9001 (<MINIO_ROOT_USER>/<MINIO_ROOT_PASSWORD>)
- Airflow UI: http://localhost:8080 (admin/admin)

## Mode spiders dedies uniquement

Par defaut, le service tourne en mode **dedie**:
- seuls les sites avec dossier spider propre sont actives
- les sites deep_crawler (sans dossier dedie) sont desactives

Variable:
```bash
DEDICATED_SPIDERS_ONLY=true
```

### ⏰ Orchestration Airflow
- 2 DAGs configurés (HAUTE/MOYENNE priorité)
- Schedule : 2x/jour (6h, 18h) pour sites prioritaires
- Monitoring via UI : http://localhost:8080
- Logs détaillés + alertes email

## Architecture technique

```
┌─────────────┐
│  Sites Web  │ (ANPE, emploi.tg, emploitogo.com, miabejob...)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Spiders   │ (BeautifulSoup + requests)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Redis    │ (Fingerprint check)
└──────┬──────┘
       │ (si nouveau)
       ▼
┌─────────────┐
│    Kafka    │ (Raw events bus)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Airflow   │ (Orchestration + logs)
└─────────────┘
```

## Demarrage rapide (5 min)

### 1. Installation
```bash
cd talentFlow/backend/job-sourcing

# Variables environnement
cp .env.example .env

# Dependances (optionnel local)
pip install -r requirements.txt
```

### 2. Lancement infrastructure
```bash
# Tous les services Docker
docker-compose up -d

# Verification
docker-compose ps
```

### 3. Premiere execution
```bash
# Test spider
python manage.py run anpe_togo

# Tous les spiders actifs
python manage.py run all

# Validation complete
python validate_etape1.py
```

## Services & Ports

| Service | Port | Credentials | URL |
|---------|------|------------|-----|
| MinIO Console | 9001 | <MINIO_ROOT_USER>/<MINIO_ROOT_PASSWORD> | http://localhost:9001 |
| MinIO API | 9000 | - | http://localhost:9000 |
| Redis | 6379 | - | localhost:6379 |
| Airflow UI | 8080 | admin/admin | http://localhost:8080 |
| PostgreSQL | 5432 | airflow/airflow | localhost:5432 |

## Sites sources

### Haute Priorite (scraping 2x/jour)
1. **ANPE Togo** - https://anpetogo.net  
   Officiel gouvernemental - 600-1200 offres/mois

2. **emploi.tg** - https://emploi.tg  
   Plateforme majeure - 500-1000 offres/mois

3. **emploitogo.com** - https://emploitogo.com  
   Appels d'offres + privé - 300-800 offres/mois

4. **miabejob** - https://miabejob.com  
   Service RH - 400-700 offres/mois

5. **EmploiTogo.info** - https://www.emploitogo.info  
   Blog emploi / stages / bourses

6. **Wiijob** - https://wiijob.com  
   Offres Afrique francophone

7. **Lucreatif** - https://lucreatif.com/job-list/  
   Cabinet RH avec annonces detaillees

## Utilisation

### CLI Spiders Scrapy
```bash
# Lister spiders disponibles
scrapy list

# Executer spider specifique
scrapy crawl anpe_togo
scrapy crawl emploi_tg

# Ou via script
python run_spider.py anpe_togo
python run_spider.py all
```

### Validation pipeline
```bash
# Test complet (Docker + Redis + MinIO + Airflow)
python validate_etape1.py

# Resultat attendu :
# PASS - docker_services
# PASS - redis_connectivity
# PASS - minio_connectivity
# PASS - airflow_connectivity
# SCORE: 4/4 tests valides
```

## Documentation

- [Guide Démarrage Rapide](QUICKSTART.md) - 5 minutes
- [Documentation Complète Etape 1](docs/ETAPE_1_COMPLETE.md) - Architecture détaillée
- [Variables Environnement](.env.example) - Configuration

---

**Statut** : Production Ready  
**Developpe avec** : Python 3.11, Docker, Redis, MinIO, Airflow, BeautifulSoup

## Utilisation

### Demarrer les services Docker
```bash
docker-compose up -d
```

### Lister les spiders disponibles
```bash
python manage.py list
```

### Executer un spider specifique
```bash
python manage.py run togo_jobs
```

### Executer tous les spiders
```bash
python manage.py run all
```

## Ajouter un nouveau site

1. Creer un nouveau dossier dans `spiders/` avec le nom du site
2. Ajouter les fichiers suivants :
   - `__init__.py` : Initialisation du module
   - `config.yml` : Configuration des sources et selecteurs
   - `spider.py` : Logique de scraping (herite de BaseSpider)
   - `parser.py` : Logique de parsing des donnees
3. Le spider sera automatiquement detecte par `manage.py`

## Configuration

### Variables d'environnement
Copier `.env.example` vers `.env` et configurer :
- `MINIO_ENDPOINT` : Endpoint MinIO
- `MINIO_ACCESS_KEY` : Cle d'acces MinIO
- `MINIO_SECRET_KEY` : Cle secrete MinIO
- `REDIS_HOST` : Hote Redis
- `REDIS_PORT` : Port Redis

### Configuration globale
Editer `configs/global_config.yml` pour les parametres partages.

### Configuration par site
Editer `spiders/<site>/config.yml` pour les parametres specifiques.

## Anti-duplication (Fingerprinting)
- Chaque offre est identifiee par un hash SHA256 (URL + contenu)
- Les hash sont stockes dans Redis avec une TTL de 30 jours
- Si un hash existe deja, l'offre n'est pas publiee dans Kafka
- Cela evite de saturer le stockage avec des doublons
