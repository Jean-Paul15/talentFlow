# Migration Qdrant Cloud

## Objectif

Préparer une migration propre de `Qdrant` vers `Qdrant Cloud` sans changer le code applicatif.

Le moteur principal reste `Qdrant`, mais:
- en local: `QDRANT_URL=http://qdrant:6333`
- en cloud: `QDRANT_URL=https://<cluster>.cloud.qdrant.io:6333`

Le service `search-engine` lit déjà:
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION`

## Décision recommandée

Pour l'instant:
- garder `Qdrant local` en développement et pour la démo
- garder `dense-only` pour le user-facing
- utiliser `Qdrant Cloud` seulement plus tard si le besoin est:
  - opérations simplifiées
  - sauvegardes
  - haute disponibilité
  - monitoring externe

Ne pas migrer vers le cloud uniquement pour chercher un gain de latence si les services applicatifs restent sur la même machine locale: le principal gain actuel vient du chemin `dense-only`, pas du hosting du cluster.

## Variables d'environnement

### Local

```env
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=talentflow_jobs
QDRANT_HYBRID_ENABLED=false
QDRANT_ENABLE_SPARSE=false
```

### Cloud

```env
QDRANT_URL=https://xxxxxx.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxxxxxxxxxx
QDRANT_COLLECTION=talentflow_jobs
QDRANT_HYBRID_ENABLED=false
QDRANT_ENABLE_SPARSE=false
```

## Étapes de migration

1. Créer le cluster Qdrant Cloud.
2. Récupérer:
   - URL du cluster
   - API key
3. Mettre à jour `backend/.env`:
   - `QDRANT_URL`
   - `QDRANT_API_KEY`
4. Garder `QDRANT_COLLECTION=talentflow_jobs`.
5. Relancer:
   - `search-engine`
   - `recommendation`
6. Déclencher un reindex complet:
   - `POST /index/reindex?force=true`
7. Vérifier:
   - `GET /health`
   - `GET /index/sync-status`
   - un test réel CV -> offres

## Vérifications attendues

- `search-engine` sain
- `doc_count` cohérent
- `sync-status = in_sync`
- temps de réponse utilisateur stable

## Points d'attention

1. Si `Qdrant Cloud` est utilisé, ne pas oublier `QDRANT_API_KEY`.
2. Garder `dense-only` en prod utilisateur tant que l'hybride n'apporte pas un vrai gain mesuré.
3. Éviter une latence réseau inutile:
   - si possible, héberger `search-engine` proche du cluster Qdrant
4. La migration ne dispense pas de:
   - déduplication
   - qualité documentaire
   - politique `expired/stale`

## Commandes utiles

### Vérifier le service

```bash
curl http://localhost:8003/health
```

### Reindex complet

```bash
curl -X POST "http://localhost:8003/index/reindex?force=true"
```

### Vérifier la synchro

```bash
curl http://localhost:8003/index/sync-status
```

## Verdict

La migration Qdrant Cloud est prête sur le plan configuration.

La bonne stratégie actuelle est:
- `Qdrant local` maintenant
- `Qdrant Cloud` plus tard si besoin d'exploitation/HA
- sans changer le code applicatif
