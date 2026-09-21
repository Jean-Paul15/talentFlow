# API Gateway & Routes Architecture

## Responsabilité

L'API Gateway (NestJS GraphQL) expose les endpoints pour l'application.

## Routes Principales

### Analyse Gaps (CV vs Offre)

**Async** : POST `/api/cv/gaps/async`
- Entrée : CV text, job title, company (optionnel)
- Retour : task_id immédiatement
- Background : Analyze en async, disponible via `/api/cv/state/{task_id}`

**Sync** : POST `/api/cv/gaps`
- Entrée : CV text, job title, company
- Retour : Résultat direct (bloque jusqu'à terminé)

**Réponse** :
```
{
  points_forts: ["Python", "FastAPI", ...],
  competences_manquantes: ["Rust", ...],
  recommendation: "Oui" | "Non" | "Avec reserves",
  conseils: ["Apprendre Rust", ...],
  confiance: 85.5 (%)
}
```

### Amélioration CV

**Async** : POST `/api/cv/improve-cv/async`
- Entrée : CV text, target job title
- Retour : task_id

**Sync** : POST `/api/cv/improve-cv`
- Entrée : CV text, target job title
- Retour : Résultat direct

**Réponse** :
```
{
  mots_cles_ajouter: ["LLM", "RAG", ...],
  reformulations: [{avant: "...", apres: "...", raison: "..."}, ...],
  sections_renforcer: ["Expériences", ...],
  conseils_ats: ["Ajouter keywords", ...]
}
```

### Explication Offre

**Async** : POST `/api/cv/explain-job/async`
- Entrée : Job title, company (optionnel), description
- Retour : task_id

**Sync** : POST `/api/cv/explain-job`
- Entrée : Job title, company, description
- Retour : Résultat direct

**Réponse** :
```
{
  ce_quil_faut_vraiment: "Entreprise cherche quelqu'un capable de...",
  profil_ideal: "Dev full-stack avec 5-7 ans, leadership...",
  defis_poste: ["Stress deadline", "Complexité système", ...],
  opportunites: ["Apprendre tech moderne", "Team solide", ...]
}
```

## Gestion Requêtes Async

Quand endpoint async est appelé :

1. **Create Task** : Crée une tâche avec ID unique
2. **Add to Queue** : Ajoute le travail à la file
3. **Return Immédiatement** : API répond avec task_id
4. **Background Worker** : Lance le traitement sans bloquer
5. **Update State** : Chaque étape met à jour progress
6. **Frontend Poll** : Interroge `/api/cv/state/{task_id}` toutes les 500ms
7. **Final Result** : Quand terminé, disponible dans final_result

## Polling vs WebSocket

**Polling** (GET `/api/cv/state/{task_id}`):
- Avantage : Simple, fonctionne partout
- Désavantage : Latence (req toutes les 500ms), surcharge réseau

**WebSocket** (WS `/api/cv/ws/state/{task_id}`):
- Avantage : Temps réel, efficace, UX fluide
- Désavantage : Dépend de support WebSocket

Recommandé : WebSocket pour mobile app, Polling pour web simple.

## Validation & Erreurs

Chaque requête passe par :

1. **DTO Validation** : Pydantic valide schéma et tailles
2. **LLM Processing** : OutputParser valide structure JSON
3. **Error Handling** : Si erreur, state = FAILED + message d'erreur

Résultat : Garantie que réponse est toujours valide JSON.

## Patterns

Le code API suit Factory Pattern (endpoint_factory.py) :
- 1 fonction pour créer tous les endpoints async
- 1 fonction pour créer tous les endpoints sync
- Élimine 90% du code de boilerplate
- Facile d'ajouter nouvel endpoint (1 ligne)
