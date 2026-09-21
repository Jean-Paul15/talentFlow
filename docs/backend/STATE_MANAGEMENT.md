# State Management Architecture

## Concept

Le state management track l'état d'une analyse en temps réel. Permet au frontend d'afficher une progress bar et recevoir résultats partiels.

## Flux d'une Analyse Async

1. **Create** : Frontend appelle POST `/api/cv/gaps/async` avec CV + offre
2. **Task créée** : API crée une task_id et retourne immédiatement
3. **Background job** : API lance le traitement en arrière-plan (sans bloquer)
4. **Updates état** : Service update l'état tous les 10-20% (progress)
5. **Frontend poll** : GET `/api/cv/state/{task_id}` régulièrement (500ms)
6. **Affiche progress** : Frontend montre 10%... 40%... 70%... 100%
7. **Résultat final** : Quand 100%, retourne résultat JSON

Alternative (meilleur) : WebSocket au lieu de polling
- Frontend s'abonne via `/api/cv/ws/state/{task_id}`
- Reçoit updates en temps réel dès qu'état change
- Ferme connexion quand analyse terminée
- Zéro latence, meilleure UX

## État d'une Analyse

```
Champs de l'état :
- task_id : Identifiant unique
- status : pending | processing | completed | failed
- step : validation | extraction | analysis | formatting | completed
- progress : 0-100 (%)
- message : "Extraction en cours..." (pour display)
- partial_result : Résultat partiellement disponible
- final_result : Résultat final quand terminé
- error : Message d'erreur si failed
- timestamps : created_at, updated_at
```

## Implémentation

**state_manager.py** (singleton) :
- Stocke tous les états en mémoire (Dict)
- Peut migrer vers Redis pour persistence
- 1 instance globale partagée par tous les threads

**AnalysisState** (class) :
- Représente l'état d'UNE analyse
- Model Pydantic avec validation
- Méthode update() appelée à chaque étape

**state_helper.py** :
- Fonction execute_with_state()
- Appelle analysis_state_manager.update_state() automatiquement
- Gère les 5 étapes et progress 10/40/70/90/100

## Avantages

**Pour Frontend** :
- Sait quand analyse terminée
- Affiche progress bar realiste
- Reçoit résultat partiel dès dispo
- Peut faire autre chose en attendant

**Pour Backend** :
- Non-blocking : API reste responsive
- Scalable : 10 analyses simultanées sans problème
- Facile à debugger : voir où analyse bloque

**Pour Produit** :
- UX fluide et temps réel
- Pas de "chargement blanc" frustrant
- Utilisateur sait ce qui se passe
