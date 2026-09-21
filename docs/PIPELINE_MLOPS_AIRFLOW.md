# PIPELINE MLOPS AIRFLOW - ANALYSE APPROFONDIE

## JUSTIFICATION AIRFLOW

### Pourquoi un Orchestrateur
Réentraînement ML n'est pas un script isolé mais un workflow multi-étapes :
1. Vérifier besoin réentraînement (nouvelles données?)
2. Collecter données PostgreSQL
3. Entraîner modèle LightGBM
4. Évaluer performance (NDCG)
5. Décider déploiement ou rollback
6. Notifier équipe (Slack, email)
7. Nettoyer fichiers temporaires

**Sans orchestrateur** : Script bash monolithique, gestion erreurs complexe, pas de monitoring.
**Avec Airflow** : DAG déclaratif, retry automatique, UI monitoring, historique exécutions.

### Alternatives Rejetées

#### Cron Jobs
**Limites** :
- Pas de gestion dépendances inter-tâches
- Pas de retry automatique
- Logs dispersés (syslog, stdout)

#### Kubernetes CronJobs
**Limites** :
- Pas de branching conditionnel (if/else)
- Difficile de passer données inter-pods
- UI monitoring limité

#### Prefect / Dagster
**Avantages** : Modernes, Python-first.
**Airflow Choisi** : Maturité (10+ ans), large communauté, intégrations (Slack, PagerDuty).

---

## ARCHITECTURE DU DAG

### Déclencheurs
**Schedule** : `0 2 * * 1` (Lundi 02h00).
**Justification** :
- Nuit = faible charge serveur
- Lundi = accumulation interactions weekend
- Hebdomadaire = compromis fraîcheur/coût

**Déclencheurs Manuels** :
- UI Airflow : Bouton "Trigger DAG"
- API : `POST /api/v1/dags/ml_retraining/dagRuns`

**Cas d'Usage Manuel** : Bug détecté, correctif données, A/B test nouveau modèle.

### Tâches et Dépendances

#### 1. check_retraining_needed (PythonOperator)
**Logique** :
```
nouvelles_interactions = TrainingDataCollector.count_new_interactions()
jours_depuis_dernier_entrainement = calculate_days_since_last_training()

if nouvelles_interactions >= 50 OR jours_depuis_dernier_entrainement >= 7:
    return 'collect_training_data'
else:
    return 'skip_retraining'
```

**Sortie** : BranchPythonOperator → route workflow.

**Justification Seuils** :
- 50 interactions = minimum statistiquement significatif pour améliorer modèle
- 7 jours = éviter stagnation même si peu d'interactions

#### 2. skip_retraining (EmptyOperator)
**Rôle** : No-op, termine DAG sans erreur.
**Logging** : "Skipping: Only X new interactions, last training Y days ago."

#### 3. collect_training_data (PythonOperator)
**Actions** :
1. Query PostgreSQL : `SELECT * FROM user_interactions WHERE created_at > last_training_date`
2. Calcul labels relevance
3. Extraction features_json vers DataFrame
4. Sauvegarde temporaire : `/tmp/training_features.parquet`, `/tmp/training_labels.npy`, `/tmp/training_qids.npy`
5. Push XCom : `n_samples`, `label_distribution`

**Gestion Erreurs** :
- Si PostgreSQL timeout → Retry 2× avec backoff exponentiel
- Si <100 samples total → Force bootstrap mode
- Si corruption données → Exception, DAG échoue (alerte)

#### 4. train_model (PythonOperator)
**Actions** :
1. Charger données temporaires
2. Split 80/20 train/validation
3. Entraîner LightGBM avec early_stopping
4. Sauvegarder modèle `/app/models/ranker_candidate.pkl`
5. Push XCom : `ndcg_train`, `ndcg_val`, `feature_importance`

**Timeout** : 2 heures (si dépassé, échec).
**Ressources** : Peut nécessiter 4 GB RAM pour >100k samples.

#### 5. evaluate_model (BranchPythonOperator)
**Logique** :
```
ndcg_val = ti.xcom_pull(task_ids='train_model', key='ndcg_val')

if ndcg_val >= 0.65:
    return 'deploy_model'
else:
    return 'rollback_model'
```

**Seuil 0.65** : Empirique, correspond à "qualité acceptable" en production.

#### 6a. deploy_model (PythonOperator)
**Actions** :
1. Archiver ancien modèle : `mv /app/models/ranker.pkl /app/models/archive/ranker_{timestamp}.pkl`
2. Promouvoir candidat : `mv /app/models/ranker_candidate.pkl /app/models/ranker.pkl`
3. Mettre à jour metadata : `/app/models/model_info.json` (version, NDCG, date)
4. Hot-reload : Signaler service recommendation (SIGHUP ou API endpoint `/reload_model`)

**Validation Post-Deploy** :
- Test endpoint sanity check : Recommandations 5 CVs tests, vérifier pas d'exception

#### 6b. rollback_model (PythonOperator)
**Actions** :
1. Log warning : "Model NDCG X.XX below threshold, keeping previous model"
2. Supprimer candidat : `rm /app/models/ranker_candidate.pkl`
3. Push XCom : `rollback_reason`

**Pas d'Erreur** : Rollback est un succès (système protégé contre régression).

#### 7. notify_results (PythonOperator)
**Actions** :
1. Construire message résumé (nouvelles interactions, NDCG, features top 5, décision deploy/rollback)
2. Envoyer Slack webhook : Canal `#ml-monitoring`
3. Optionnel : Email équipe data

**Exemple Message** :
```
ML Retraining - SUCCESS
New Interactions: 127
NDCG Train: 0.73 | Val: 0.69
Top Features: semantic_score (0.28), skill_overlap (0.22), ...
Decision: DEPLOYED (replaced model v12 with v13)
```

#### 8. cleanup_temp_files (PythonOperator)
**Actions** :
```
rm -f /tmp/training_features.parquet
rm -f /tmp/training_labels.npy
rm -f /tmp/training_qids.npy
```

**Trigger Rule** : `all_done` (s'exécute même si tâches précédentes échouent).
**Justification** : Éviter accumulation fichiers temporaires.

### Flux Visuel
```
check_retraining_needed
    ├─→ skip_retraining → notify_results → cleanup
    └─→ collect_training_data → train_model → evaluate_model
            ├─→ deploy_model → notify_results → cleanup
            └─→ rollback_model → notify_results → cleanup
```

---

## CONFIGURATION ET TUNING

### Retries et Timeouts
**Par Défaut DAG** :
- `retries=2` : Tolérance pannes transitoires (network blips)
- `retry_delay=5min` : Évite surcharge si problème persistant
- `execution_timeout=2h` : Kill si bloqué (évite zombie tasks)

**Overrides Spécifiques** :
- `collect_training_data` : `retries=3` (PostgreSQL intermittent)
- `notify_results` : `retries=0` (si échec notification, pas critique)

### Concurrency
**DAG Level** : `max_active_runs=1`
**Justification** : Éviter 2 entraînements simultanés (conflit modèle candidat).

**Task Level** : `max_active_tasks=3`
**Justification** : collect/train/evaluate peuvent paralléliser si séquentielles.

### SLA (Service Level Agreement)
**Définition** : `sla=timedelta(hours=3)`
**Signification** : Si DAG prend >3h, alerte automatique.

**Cas Dépassement** :
- Dataset anormalement large (>1M interactions)
- Problème performance PostgreSQL/LightGBM
- Investigation requise

---

## MONITORING ET ALERTES

### Métriques Airflow Natives
**UI Airflow** :
- Durée exécution par tâche (détection régressions performance)
- Taux succès/échec DAG (trend dégradation)
- SLA misses (alertes proactives)

### Logs Structurés
Chaque tâche log JSON :
```json
{
  "task": "train_model",
  "execution_date": "2026-02-03T02:00:00Z",
  "n_samples": 1247,
  "ndcg_val": 0.68,
  "duration_seconds": 187
}
```

**Ingestion** : Elasticsearch/Kibana pour analyses historiques.

### Alertes Critiques
**Slack** :
- DAG échoue 2× consécutivement → `@channel` critique
- NDCG <0.55 → Rollback + investigation urgente
- Durée >2h → Timeout, vérifier charge serveur

**PagerDuty** : Échec 3× consécutifs → Escalation on-call.

---

## SÉCURITÉ ET GOVERNANCE

### Secrets Management
**Problème** : DATABASE_URL, SLACK_WEBHOOK sensibles.

**Solution - Airflow Connections** :
```
airflow connections add postgres_recommendation \
  --conn-type postgres \
  --conn-host db.internal \
  --conn-login mlops_user \
  --conn-password <encrypted>
```

**Accès Code** :
```python
from airflow.hooks.postgres_hook import PostgresHook
hook = PostgresHook(postgres_conn_id='postgres_recommendation')
```

**Avantage** : Secrets chiffrés dans metadata DB Airflow, pas dans code.

### Audit Trail
**Airflow Metadata** : Tout enregistré (qui a déclenché, quand, paramètres).

**Exemple Query** :
```sql
SELECT execution_date, state, duration
FROM dag_run
WHERE dag_id='ml_retraining_pipeline'
ORDER BY execution_date DESC
LIMIT 10;
```

**Cas d'Usage** : Debugging ("pourquoi modèle v14 sous-performe?"), compliance (traçabilité décisions).

---

## DÉCISIONS ARCHITECTURALES ROBUSTES

### 1. Branching Plutôt que Skip Task
**Alternative** : Toujours collecter données, décider skip dans train_model.
**Problème** : Gaspillage ressources (query PostgreSQL inutile).

**Choix** : BranchPythonOperator décide en amont.
**Avantage** : Efficacité, clarté flux (UI Airflow montre branche suivie).

### 2. XCom pour Passage Données
**Alternative** : Fichiers temporaires pour toutes inter-tasks.
**Problème** : I/O disque, gestion cleanup complexe.

**Choix** : XCom pour métadonnées (NDCG, n_samples), fichiers pour gros volumes (features DataFrame).
**Compromis** : XCom limité 48 KB (suffisant metadata), fichiers pour >10 MB.

### 3. Hot-Reload Plutôt que Redeploy Service
**Alternative** : Redéployer service recommendation (docker restart).
**Problème** : Downtime 10-30s inacceptable.

**Choix** : Signal SIGHUP ou API `/reload_model` → Service recharge modèle en mémoire.
**Implémentation** : Watchdog filesystem ou endpoint Flask.

### 4. Rollback Automatique Sans Intervention Humaine
**Alternative** : Déployer nouveau modèle, équipe surveille métriques online, rollback manuel si problème.
**Problème** : Fenêtre dégradation peut être longue (détection + action).

**Choix** : Validation NDCG validation set pré-deploy.
**Limite** : Validation set pas toujours représentatif production (distribution shift).
**Mitigation** : Canary deployment (5% trafic nouveau modèle pendant 1h, rollback si CTR baisse).

---

## ÉVOLUTIONS FUTURES

### Entraînement Incrémental
**Problème Actuel** : Réentraînement from scratch chaque fois (coûteux si >1M samples).

**Solution** : LightGBM supporte `init_model` (continuer entraînement existant).
**Implémentation** :
```python
booster = lgb.train(params, train_data, init_model='/app/models/ranker.pkl')
```

**Gain** : 10× plus rapide, modèle évolue progressivement.

### Multi-Model A/B Testing
**Idée** : Entraîner 2 modèles (différents hyperparams), router 50/50 trafic, comparer NDCG online.

**Implémentation Airflow** :
- Tâche `train_model_A` et `train_model_B` parallèles
- Déployer les 2 modèles avec suffix (`ranker_A.pkl`, `ranker_B.pkl`)
- Service recommendation lit paramètre `?model=A` ou `?model=B`

### Feature Store Integration
**Problème** : Features calculées 2× (online serving + offline training).

**Solution** : Feast Feature Store.
- Online serving lit features Redis/Cassandra (faible latence)
- Offline training lit features S3/Hive (batch)
- Garantie cohérence (même code feature engineering)

**Impact DAG** : Tâche `sync_features_to_store` avant `collect_training_data`.
