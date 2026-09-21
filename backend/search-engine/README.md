# Search Engine - Etape 3: Indexation et Recherche Semantique

Service de recherche semantique pour TalentFlow.
Il lit les offres nettoyees depuis MongoDB Silver, construit un index dense dans Qdrant et expose une API FastAPI pour la recherche utilisateur.

## Architecture

```text
MongoDB (Silver) -> Indexeur Qdrant -> API FastAPI (dense-only + filtres qualite/fraicheur)
```

## Modele d'Embeddings

**paraphrase-multilingual-MiniLM-L12-v2**
- 384 dimensions
- support multilingue
- optimisé pour la similarité sémantique courte et moyenne

## Demarrage

```bash
# Installer dependances
pip install -r requirements.txt

# Configurer variables
cp .env.example .env

# Creer la collection Qdrant
python index_jobs.py --create-index

# Indexer les offres depuis MongoDB
python index_jobs.py

# Demarrer l'API
python main.py
```

## Endpoints

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | /health | Statut du service |
| POST | /search | Recherche dense + filtres |
| POST | /search/by-vector | Recherche par vecteur |
| POST | /index/reindex | Reindex Qdrant |
| GET | /index/sync-status | Verification Mongo/Qdrant |

## Exemple de recherche

```json
POST /search
{
  "query": "developpeur Python Django",
  "location": "Lome",
  "contract_type": "CDI",
  "skills": ["Python", "Django"],
  "limit": 20
}
```

## Configuration

Variables d'environnement dans `.env`:

| Variable | Description | Defaut |
|----------|-------------|--------|
| QDRANT_URL | URL Qdrant | http://localhost:6333 |
| QDRANT_COLLECTION | Nom de la collection | talentflow_jobs |
| MONGODB_URI | URI MongoDB | mongodb://localhost:27017 |
| EMBEDDING_MODEL | Modele HF | paraphrase-multilingual-MiniLM-L12-v2 |
| QDRANT_HYBRID_ENABLED | Active le mode hybride benchmark | false |
| SEARCH_EXCLUDE_EXPIRED | Exclut les offres expirées | true |
| SEARCH_STALE_PENALTY | Penalite stale | 0.45 |
