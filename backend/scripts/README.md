# TalentFlow - Gestion Automatisée

Scripts d'automatisation intelligents pour déploiement et gestion du backend TalentFlow.

## Structure

```
backend/
├── manage.sh              # Script principal Bash (Linux/Mac)
├── manage.ps1             # Script principal PowerShell (Windows)
└── scripts/
    ├── bash/              # Modules Bash
    │   ├── env-generator.sh
    │   ├── service-manager.sh
    │   └── docker-ops.sh
    └── powershell/        # Modules PowerShell
        ├── env-generator.ps1
        ├── service-manager.ps1
        └── docker-ops.ps1
```

## Quick Start

### Linux/Mac (Bash)

```bash
# Rendre exécutable
chmod +x manage.sh

# Initialisation complète
./manage.sh init

# Démarrer tous les services
./manage.sh start

# Health check
./manage.sh health
```

### Windows (PowerShell)

```powershell
# Autoriser exécution scripts
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Initialisation complète
.\manage.ps1 init

# Démarrer tous les services
.\manage.ps1 start

# Health check
.\manage.ps1 health
```

## Commandes Disponibles

### Gestion Services

| Commande | Description | Exemple |
|----------|-------------|---------|
| `start [service]` | Démarrer service(s) | `./manage.sh start recommendation` |
| `stop [service]` | Arrêter service(s) | `./manage.sh stop job-sourcing` |
| `restart [service]` | Redémarrer service(s) | `./manage.sh restart api-gateway` |
| `rebuild [service]` | Rebuild + démarrer | `./manage.sh rebuild data-cleaning` |
| `status` | Status tous services | `./manage.sh status` |
| `health` | Health check API | `./manage.sh health` |

### Logs

```bash
# Logs récents (100 dernières lignes)
./manage.sh logs api-gateway

# Logs temps réel (follow)
./manage.sh logs recommendation -f

# PowerShell
.\manage.ps1 logs job-sourcing -Follow
```

### Gestion .env

```bash
# Créer .env interactif (secrets auto-générés)
./manage.sh env

# Régénérer CORS uniquement (dev avec *)
./manage.sh cors
```

**Fonctionnalités .env** :
- Génération automatique secrets (JWT, PostgreSQL, MinIO, Grafana)
- Prompt interactif Hugging Face API Token
- Choix CORS : Production (domaines) ou Dev (*)
- Configuration Email optionnelle
- Cryptographiquement sécurisé (OpenSSL)

### Backup & Restore

```bash
# Backup volumes (postgres, mongodb, minio, grafana)
./manage.sh backup
# Crée: backups/20260202_143052/

# Restaurer depuis backup
./manage.sh restore backups/20260202_143052
```

### Maintenance

```bash
# Nettoyage Docker (images, containers, volumes inutilisés)
./manage.sh prune

# Scaler service (3 instances search-engine)
./manage.sh scale search-engine 3
```

## Scénarios d'Usage

### 1⃣ **Premier Déploiement**

```bash
# Clone projet
git clone https://github.com/org/talentflow.git
cd talentflow/backend

# Rendre exécutable (Linux/Mac)
chmod +x manage.sh

# Init automatique
./manage.sh init
```

**Ce que fait `init` :**
1. Génère `.env` avec prompts interactifs
2. Crée réseau Docker `talentflow_network`
3. Crée dossiers `logs/` et `backups/`
4. Build toutes les images Docker
5. Démarre tous les services
6. Health check automatique après 30s

**Prompts attendus :**
```
Génération du fichier .env...

Configuration Hugging Face (pour LLM)
Hugging Face API Token [hf_XXXXX]: hf_xxxxxxxxxxxxxxxxxxx

Configuration CORS
Options:
  1) Production (https://talentflow.tg,https://app.talentflow.tg)
  2) Development (*)
Choix [1-2]: 2

Configuration Email (optionnel)
SMTP Host [smtp.gmail.com]: 
SMTP Port [587]: 
SMTP User []: 
SMTP Password []: 
```

**Résultat :**
```
Initialisation terminée!

Accès services:
  - API Gateway: http://localhost:3000
  - Grafana: http://localhost:3001 (admin / <généré>)
  - Airflow: http://localhost:8080
  - MinIO Console: http://localhost:9001
```

### 2⃣ **Développement Quotidien**

```bash
# Morning routine
./manage.sh start
./manage.sh health

# Modifier code recommendation service
code backend/recommendation/

# Rebuild + redémarrer service modifié uniquement
./manage.sh rebuild recommendation

# Voir logs en temps réel
./manage.sh logs recommendation -f

# Soir: arrêt propre
./manage.sh stop
```

### 3⃣ **Débogage Service Spécifique**

```bash
# Status global
./manage.sh status

# Health check détaillé
./manage.sh health
# Output:
# api-gateway (port 3000): HEALTHY
# job-sourcing (port 8000): UNHEALTHY
# recommendation (port 8001): HEALTHY

# Redémarrer service en erreur
./manage.sh restart job-sourcing

# Logs pour diagnostique
./manage.sh logs job-sourcing --tail=200
```

### 4⃣ **Basculer Dev ↔ Production (CORS)**

```bash
# Passer en mode Dev (CORS *)
./manage.sh cors
# Choisir option 2

# Redémarrer services concernés
./manage.sh restart api-gateway
./manage.sh restart recommendation

# Repasser en Production
./manage.sh cors
# Choisir option 1
```

### 5⃣ **Backup Avant Mise à Jour**

```bash
# Backup complet
./manage.sh backup
# Crée: backups/20260202_143052/
#   - postgres_data.tar.gz
#   - mongodb_data.tar.gz
#   - minio_data.tar.gz
#   - grafana_data.tar.gz

# Mise à jour code
git pull origin main

# Rebuild tous services
./manage.sh rebuild

# Si problème: restaurer
./manage.sh stop
./manage.sh restore backups/20260202_143052
./manage.sh start
```

### 6⃣ **Scaling Haute Charge**

```bash
# Scaler search-engine x3 (haute charge recherche)
./manage.sh scale search-engine 3

# Scaler recommendation x2 (analyse CV)
./manage.sh scale recommendation 2

# Vérifier scaling
./manage.sh status
```

## Contenu .env Généré

```env
# ==== SECRETS (Auto-générés) ====
JWT_SECRET=<32 bytes base64>
POSTGRES_PASSWORD=<32 bytes base64>
MINIO_ROOT_USER=talentflow_<random>
MINIO_ROOT_PASSWORD=<32 bytes base64>
GRAFANA_PASSWORD=<32 bytes base64>

# ==== API KEYS ====
HF_TOKEN=hf_xxxxxxxxxxxxx

# ==== CORS ====
ALLOWED_ORIGINS=* # ou https://talentflow.tg,...

# ==== DATABASE ====
POSTGRES_USER=talentflow
POSTGRES_DB=talentflow
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# ==== REDIS ====
REDIS_HOST=redis
REDIS_PORT=6379

# ==== MINIO ====
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=false

# ==== ELASTICSEARCH ====
ES_HOST=elasticsearch
ES_PORT=9200

# ==== MONGODB ====
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DB=talentflow_silver

# ==== EMAIL (Optionnel) ====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=

# ==== SERVICES PORTS ====
API_GATEWAY_PORT=3000
JOB_SOURCING_PORT=8000
RECOMMENDATION_PORT=8001
DATA_CLEANING_PORT=8002
SEARCH_ENGINE_PORT=8003
```

## Services Disponibles

| Service | Port | Description |
|---------|------|-------------|
| **api-gateway** | 3000 | Point d'entrée NestJS |
| **job-sourcing** | 8000 | Scrapy web scraping |
| **recommendation** | 8001 | RAG LLM Llama 3 |
| **data-cleaning** | 8002 | NLP + enrichissement |
| **search-engine** | 8003 | Elasticsearch queries |
| **postgres** | 5432 | DB utilisateurs |
| **redis** | 6379 | Cache + sessions |
| **elasticsearch** | 9200 | Index offres |
| **minio** | 9000 | Data lake S3 |
| **mongodb** | 27017 | Offres nettoyées |

## 🆘 Troubleshooting

### Problème: Service ne démarre pas

```bash
# Vérifier logs
./manage.sh logs <service>

# Rebuild complet
./manage.sh stop
./manage.sh rebuild <service>
```

### Problème: Port déjà utilisé

```bash
# Trouver processus
netstat -tulpn | grep :3000  # Linux
Get-NetTCPConnection -LocalPort 3000  # PowerShell

# Arrêter services proprement
./manage.sh stop
```

### Problème: Erreur .env

```bash
# Régénérer .env
mv .env .env.backup
./manage.sh env
```

### Problème: Docker disk space

```bash
# Nettoyage agressif
./manage.sh prune

# Vérifier espace
docker system df
```

## Monitoring Post-Démarrage

```bash
# Health check complet
./manage.sh health

# Status containers
./manage.sh status

# Logs temps réel tous services
./manage.sh logs -f

# Accès web interfaces
open http://localhost:3000        # API Gateway
open http://localhost:3001        # Grafana
open http://localhost:8080        # Airflow
open http://localhost:9001        # MinIO Console
```

## Sécurité

- Secrets auto-générés (OpenSSL)
- .env exclu du Git (.gitignore)
- CORS configurable (dev vs prod)
- Backups automatisés
- Gestion propre des credentials

## Références

- Docker Compose: https://docs.docker.com/compose/
- OpenSSL: https://www.openssl.org/docs/
- Hugging Face: https://huggingface.co/settings/tokens

---

**Développé pour simplifier la vie des devs TalentFlow**
