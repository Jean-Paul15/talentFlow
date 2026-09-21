# Etape 2: Nettoyage, Deduplication et Enrichissement

Service de transformation des donnees Bronze (MinIO) vers Silver (MongoDB).

## Architecture

```
MinIO (Bronze)          Pipeline               MongoDB (Silver)
    |                      |                        |
    v                      v                        v
[raw-data/]  -->  [TextCleaner]  -->  [jobs collection]
                  [Deduplicator]
                  [SkillEnricher]
```

## Decouplage Source

Le pipeline est **agnostique de la source**:
- Lit TOUT depuis MinIO, peu importe le site d'origine
- Le contrat est le format JSON standardise
- Ajouter un nouveau site = pas de modification de l'Etape 2

## Composants

### Core
- `minio_reader.py` - Lecture Bronze depuis MinIO
- `mongo_writer.py` - Ecriture Silver vers MongoDB
- `config_loader.py` - Chargement configuration YAML

### Processors
- `text_cleaner.py` - Nettoyage texte avec Unstructured
- `deduplicator.py` - Hash unique SHA256(titre+entreprise)
- `skill_enricher.py` - Extraction skills via Mistral -> Qwen local optionnel -> NER/patterns

### Pipeline
- `pipeline.py` - Orchestration complete
- `run_pipeline.py` - Point d'entree CLI

## Execution

```bash
# Toutes les offres des 24 dernieres heures
python run_pipeline.py --since-hours 24

# Filtrer par site
python run_pipeline.py --site emploi_tg

# Traitement complet (sans filtre date)
python run_pipeline.py --full
```

## Docker

```bash
# Demarrer MongoDB
docker-compose up -d mongodb

# Executer le pipeline
docker-compose run --rm data-cleaner
```

## Airflow

Le DAG `etape2_cleaning_enrichment` s'execute toutes les 6 heures.

## Technologies
- Traitement des données : Python
- LLM principal : Mistral
- Fallback local optionnel : Qwen2.5:3b
- NLP local deterministe : Hugging Face + regex
- Base de données : MongoDB
