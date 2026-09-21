# Strategie de Scraping TalentFlow

## Architecture Parallelisme

### Niveau 1: Scrapy (intra-spider)
- **CONCURRENT_REQUESTS**: 8 requetes globales simultanees
- **CONCURRENT_REQUESTS_PER_DOMAIN**: 2 max par site (respectueux)
- **Avantage**: Scrapy gere nativement l'asyncio (Twisted reactor)

### Niveau 2: Airflow (inter-spiders)
- **TaskGroup parallele**: 2 spiders en meme temps
- **Priority 1**: ANPE + emploi.tg en parallele (3x/jour)
- **Priority 2**: miabejob + emploitogo.com en parallele (2x/jour)
- **Priority 3**: Sites secondaires sequentiels (1x/jour)

### Niveau 3: Multi-DAG
- **3 DAGs independants** tournant selon schedules differents
- **max_active_runs=1**: Previent chevauchement meme DAG
- **Isolation**: Chaque DAG a son propre TaskGroup

## Strategie Frequences

Basee sur analyse fichier sites-offres-emploi-togo-international.md :

| Site | Volume | Frequence MAJ | Schedule Airflow | Raison |
|------|--------|--------------|------------------|--------|
| **ANPE Togo** | 600-1200 | Quotidienne | 3x/jour (6h, 14h, 20h) | Site officiel, haute activite |
| **emploi.tg** | 500-1000 | Quotidienne | 3x/jour (7h, 15h, 21h) | Plateforme majeure |
| **miabejob** | 400-700 | Quotidienne | 2x/jour (8h, 16h) | Service RH qualitatif |
| **emploitogo.com** | 300-800 | Quotidienne | 2x/jour (9h, 17h) | Appels offres |
| **emploitogo.info** | 200-500 | Hebdomadaire | 1x/jour (10h) | Bourses/stages |
| **rmo_togo** | 300-600 | Hebdomadaire | 1x/jour (11h) | RSS feed |

## Gestion Reprise (Fault Tolerance)

### 1. Retry Exponential Backoff (Airflow)
```python
retries: 3
retry_delay: 5 min
retry_exponential_backoff: True
max_retry_delay: 1h
```
- Retry 1: +5 min
- Retry 2: +10 min
- Retry 3: +20 min

### 2. Scrapy Retry Middleware
```python
RETRY_TIMES: 3
RETRY_HTTP_CODES: [500, 502, 503, 504, 408, 429]
```
Retry automatique sur erreurs temporaires

### 3. Redis Fingerprinting
- **Idempotence garantie**: Meme offre scrapee 2x = 1 seule stockee
- **TTL 30 jours**: Anti-duplication sur periode glissante
- **Reprise propre**: Re-run spider apres crash = skip duplicates

### 4. MinIO Transactionalite
- Upload atomique par job
- Path unique: `{site}/{date}/{hash}.json`
- Pas de corruption partielle

### 5. Airflow State Management
- **depends_on_past: False**: DAG run independants
- **catchup: False**: Pas de backfill automatique (evite spam)
- **max_active_runs: 1**: Un seul run actif par DAG

## Optimisations Performances

### 1. Scrapy Async
- Twisted reactor asyncio
- Non-blocking I/O
- 8 requetes paralleles par spider

### 2. Rate Limiting Intelligent
```python
AUTOTHROTTLE_ENABLED: True
TARGET_CONCURRENCY: 2.0
```
Adaptation automatique selon reponse serveur

### 3. Randomized Delays
```python
RANDOMIZE_DOWNLOAD_DELAY: True
```
Pattern naturel, evite detection bot

### 4. Pipeline Efficace
- Fingerprint check AVANT parsing complet
- Drop items en pipeline = pas de parsing inutile
- Logs structures pour monitoring

## Monitoring Production

### Metriques Airflow
- Task success rate par spider
- Duree execution moyenne
- Retry counts
- Alerts email si 3 echecs consecutifs

### Metriques Scrapy
- Items scraped/dropped
- Request success rate
- Response time moyens
- Stats par domaine

### Metriques Redis
- Fingerprints total
- Hit rate (duplicates %)
- Memory usage
- TTL distribution

### Metriques MinIO
- Objects stored per site
- Storage growth rate
- Upload failures

## Scalabilite Future

### Phase 2: Sites Internationaux
- **AfricaWork** (37 pays): 1 spider par pays, DAG dediee
- **Indeed/LinkedIn**: Proxies rotatifs, API si possible
- **Glassdoor**: Enrichissement avis employes

### Phase 3: Distributed Scraping
- Scrapyd cluster (3+ nodes)
- Load balancing par site
- Redis Cluster pour fingerprints
- MinIO multi-node

### Phase 4: Real-time
- Scrapy Cloud (Zyte)
- Webhooks sur nouvelles offres
- Stream processing (Kafka)
