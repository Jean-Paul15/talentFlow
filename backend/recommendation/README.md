# RAG Service - Etape 4: Moteur de Raisonnement IA

Service d'analyse et recommandations pour TalentFlow.
Utilise LangChain + Mistral (Hugging Face) pour le raisonnement.

## Fonctionnalites

| Fonction | Description |
|----------|-------------|
| Gap Analysis | Comparaison CV vs Offre, competences acquises/manquantes |
| Matching Score | Score 0-100% avec details par critere |
| Aide CV | Suggestions de mots-cles ATS et reformulations |

## Architecture

```
CV Upload -> Parser -> Embeddings -> Matching
                                        |
                                        v
                              LLM (Mistral 7B) -> Analyse
```

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
# Ajouter HUGGINGFACE_API_KEY dans .env
python main.py
```

## Endpoints

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | /cv/upload | Upload et analyse un CV |
| POST | /analyze/match | Analyse CV vs Offre |
| POST | /analyze/improve-cv | Suggestions d'amelioration |
| GET | /health | Statut du service |

## Workflow

```bash
# 1. Upload CV
curl -X POST -F "file=@mon_cv.pdf" http://localhost:8003/cv/upload

# 2. Analyser match avec une offre
curl -X POST http://localhost:8003/analyze/match \
  -H "Content-Type: application/json" \
  -d '{"cv_id": "abc123", "job_id": "xyz789"}'
```