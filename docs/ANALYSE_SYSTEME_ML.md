# ANALYSE APPROFONDIE DU SYSTÈME ML DE RECOMMANDATION

## COMPORTEMENT SANS DONNÉES INITIALES

### Stratégie Bootstrap
Le système démarre en **mode bootstrap** lorsqu'aucune interaction utilisateur n'est disponible. Au lieu de crasher ou d'attendre indéfiniment, il génère des pseudo-labels intelligents basés sur des heuristiques validées par la recherche académique en Information Retrieval.

### Flux de Dégradation Gracieuse
1. **Phase 1 - Aucun Modèle** : Scoring heuristique pondéré (semantic 35%, skills 25%, experience 15%)
2. **Phase 2 - Bootstrap** : Génération de 1000 échantillons synthétiques avec pseudo-labels calculés
3. **Phase 3 - Premier Entraînement** : Modèle LightGBM entraîné sur données bootstrap
4. **Phase 4 - Production** : Modèle entraîné sur interactions réelles (≥100 échantillons)

### Garanties de Robustesse
- **Aucun arrêt de service** : Le système reste opérationnel même sans modèle ML
- **Transition transparente** : Passage automatique de heuristique → bootstrap → ML
- **Qualité progressive** : Amélioration continue avec accumulation des interactions

---

## POURQUOI LIGHTGBM PLUTÔT QU'UN AUTRE ALGORITHME

### Comparaison avec Alternatives

#### XGBoost
- **Avantages XGBoost** : Maturité, large adoption, excellente documentation
- **Avantages LightGBM** : 10x plus rapide sur grands datasets, consommation mémoire 3x inférieure
- **Choix** : LightGBM car latence critique (temps réponse <500ms) et évolutivité future

#### CatBoost
- **Avantages CatBoost** : Gestion native des catégorielles, robustesse aux valeurs manquantes
- **Avantages LightGBM** : Support natif du ranking (LambdaRank), intégration NDCG
- **Choix** : LightGBM car Learning-to-Rank est un use case premier classe, pas une extension

#### Modèles Deep Learning (RankNet, LambdaMART neural)
- **Avantages DL** : Capacité d'apprentissage de patterns complexes non-linéaires
- **Désavantages DL** : Besoin de dizaines de milliers d'échantillons, temps entraînement long, difficulté interprétation
- **Choix** : LightGBM car bootstrap avec petits datasets (<1000 samples), entraînement rapide (minutes vs heures), feature importance explicable

### Forces Spécifiques de LightGBM pour le Ranking

#### Objectif LambdaRank Natif
L'objectif `lambdarank` optimise directement la métrique NDCG (Normalized Discounted Cumulative Gain), contrairement aux algorithmes de classification/régression qui optimisent des proxies (log-loss, MSE).

**Implication** : Le modèle apprend à maximiser la qualité du classement global, pas seulement la précision individuelle de chaque prédiction.

#### Métrique NDCG Alignée avec Business
NDCG pénalise davantage les erreurs en haut de classement (top 5 résultats) que celles en bas. C'est exactement ce qu'on veut : les 3 premières recommandations doivent être excellentes.

**Formule** : NDCG@k = DCG@k / IDCG@k où DCG privilégie les documents pertinents en haut de liste.

---

## PYTORCH & CUDA : DÉLÉGATION GPU STRATÉGIQUE

### Pourquoi PyTorch Alors que LightGBM Suffit

#### Séparation des Responsabilités
- **PyTorch + CUDA** : Génération d'embeddings sémantiques (sentence-transformers)
- **LightGBM** : Ranking sur features tabulaires structurées

#### Charge Computationnelle
L'embedding d'un CV de 2000 mots avec un modèle multilingual nécessite :
- **CPU** : ~800ms par CV (calcul séquentiel sur matrices)
- **GPU** : ~50ms par CV (parallélisation massive sur tenseurs)

**Ratio** : GPU est 16x plus rapide pour cette opération spécifique.

#### Choix Architectural
Ne pas utiliser GPU pour embeddings forcerait :
- Soit accepter 800ms de latence (inacceptable)
- Soit pré-calculer tous les embeddings (impossible si CV dynamiques)

### Fallback CPU Automatique
Si GPU indisponible :
1. **Détection** : `torch.cuda.is_available()` retourne False
2. **Fallback** : `device = torch.device('cpu')`
3. **Impact** : Latence augmente mais service reste opérationnel
4. **Alerte** : Log WARNING pour monitoring

---

## FEATURES ML : GESTION DES DONNÉES MANQUANTES

### Problème Soulevé
Features comme `company_reputation`, `application_rate`, `contract_type` peuvent être absentes dans la base de données.

### Solution : Features Optionnelles avec Valeurs par Défaut Intelligentes

#### Stratégie de Fallback
Chaque feature possède une valeur neutre (0.5) qui signifie "information inconnue, ne pénalise ni ne favorise".

**Exemple** :
```
company_reputation manquante → 0.5 (neutre)
application_rate manquante → 0.5 (neutre)
contract_type_match manquant → 0.5 (pas de bonus/malus)
```

#### Pourquoi 0.5 et pas 0 ou 1
- **0** impliquerait "mauvais candidat" (faux négatif)
- **1** impliquerait "excellent candidat" (faux positif)
- **0.5** signifie "je ne sais pas, les autres features décideront"

#### Robustesse Mathématique
LightGBM utilise des arbres de décision qui apprennent automatiquement à ignorer les features peu informatives. Si `company_reputation` est toujours 0.5, le modèle réduira son importance dans les splits.

### Features Obligatoires vs Optionnelles

**Obligatoires** (crash si absentes) :
- `semantic_score` : Calculé par Elasticsearch, toujours présent
- `skill_overlap` : Extrait du CV et job description, toujours calculable

**Optionnelles** (0.5 si absentes) :
- `company_reputation`, `application_rate`, `contract_type_match`, etc.

---

## STOCKAGE DES DONNÉES D'ENTRAÎNEMENT

### Base de Données : PostgreSQL

#### Schéma de Table
**Table** : `user_interactions`
**Colonnes** :
- `user_id` (TEXT) : Identifiant utilisateur
- `job_id` (TEXT) : Identifiant offre
- `cv_id` (TEXT) : Identifiant CV utilisé
- `interaction_type` (ENUM) : VIEW, CLICK, SAVE, APPLY, REJECT
- `semantic_score` (FLOAT) : Score Elasticsearch au moment de l'interaction
- `ml_score` (FLOAT) : Score ML (NULL si heuristique)
- `features_json` (JSONB) : Features complètes sérialisées
- `created_at` (TIMESTAMP) : Horodatage
- `session_id` (TEXT) : Identification de session

#### Pourquoi PostgreSQL et pas Elasticsearch
- **Transactions ACID** : Garantie cohérence des labels
- **Aggregations complexes** : Calcul de statistiques d'entraînement
- **JSONB performant** : Stockage flexible des features sans schéma rigide
- **Maturité** : Backup, réplication, monitoring éprouvés

### Cycle de Vie des Données
1. **Collecte** : Chaque interaction API → INSERT dans PostgreSQL
2. **Accumulation** : Minimum 50 interactions avant réentraînement
3. **Extraction** : Query SQL récupère features + labels calculés
4. **Entraînement** : LightGBM consomme DataFrames Pandas
5. **Archive** : Modèles versionnés dans `/app/models/archive/`

---

## SYSTÈME DE CACHE : REDIS POUR PERFORMANCE

### Problème Identifié
Requêtes identiques (même CV, même paramètres) recalculent tout : embeddings GPU, ranking ML, post-processing.

### Solution : Cache Multi-Niveau

#### Niveau 1 : Cache Embeddings
**Clé** : `emb:{hash(cv_text)}`
**Valeur** : Vector embedding (768 dimensions)
**TTL** : 1 heure
**Gain** : Évite calcul GPU répété

#### Niveau 2 : Cache Recommandations
**Clé** : `ml_rank:{hash(cv_id + filters)}`
**Valeur** : Liste d'IDs d'offres avec scores
**TTL** : 10 minutes
**Gain** : Évite requête Elasticsearch + ranking ML

#### Invalidation Intelligente
- **Nouvelle offre publiée** : Invalide tous les caches recommandations
- **CV modifié** : Invalide cache embedding + recommandations de ce CV
- **Modèle ML réentraîné** : Invalide tous les caches ranking

### Impact Performance Attendu
- **Hit Rate Cible** : 60% (utilisateurs affinent filtres sans changer CV)
- **Réduction Latence** : 800ms → 30ms pour requête cachée
- **Réduction Charge GPU** : 40% moins d'embeddings calculés

---

## DEVISE DYNAMIQUE : FIN DU HARDCODING EUR

### Problème Originel
Code contenait `currency="EUR"` en dur, impossible de supporter USD, XOF, etc.

### Solution : Configuration Contextuelle

#### Détection Automatique
1. **Paramètre API** : `?currency=XOF` explicite
2. **Profile Utilisateur** : `user.preferred_currency` (stocké en DB)
3. **Géolocalisation** : IP → pays → devise locale
4. **Fallback** : Variable d'environnement `DEFAULT_CURRENCY`

#### Format Standardisé
Utilisation de codes ISO 4217 (XOF, EUR, USD) dans toute l'application.

**Exemple** :
```
User au Togo → XOF détecté
Salaire affiché : 3 500 000 XOF (au lieu de 5 300 EUR hardcodé)
```

### Conversion Automatique
Intégration API de change (ex: frankfurter.app gratuite) pour afficher équivalences :
```
Salaire: 60 000 EUR (~39M XOF)
```

---

## GARANTIES DE ROBUSTESSE GLOBALE

### Principe : Fail-Safe à Chaque Étape
Aucun composant ne peut crasher le système entier.

#### Matrice de Fallback

| Composant | Échec Possible | Fallback Automatique |
|-----------|----------------|----------------------|
| GPU | Indisponible | CPU avec latence accrue |
| Modèle ML | Non entraîné | Scoring heuristique |
| Cache Redis | Serveur down | Calcul direct sans cache |
| PostgreSQL | Timeout | Skip tracking, log warning |
| Elasticsearch | Cluster rouge | Retour liste vide gracieux |

### Tests de Résilience
Chaque service doit passer ces scénarios :
1. **Cold Start** : Démarrage sans aucune donnée préexistante
2. **Partial Failure** : 50% des features manquantes
3. **Resource Exhaustion** : CPU 100%, mémoire limitée
4. **Network Partition** : Perte connexion inter-services

---

## MÉTRIQUES DE SUCCÈS

### Objectifs Mesurables
- **Latence P95** : <500ms (end-to-end)
- **Cache Hit Rate** : >60%
- **NDCG@10** : >0.70 après 1000 interactions
- **Bootstrap Quality** : NDCG@10 >0.50 (avant données réelles)
- **Uptime** : 99.9% (tolérance pannes composants)

### Monitoring Continue
Dashboard Prometheus/Grafana affichant :
- Taux utilisation GPU vs CPU pour embeddings
- Distribution scores ML (détection drift)
- Feature importance (évolution dans le temps)
- Taux fallback heuristique (indicateur santé modèle)
