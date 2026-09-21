# SERVICE DE RANKING ML - ANALYSE APPROFONDIE

## RESPONSABILITÉ UNIQUE

### Rôle dans l'Architecture
Le service de ranking est l'arbitre final qui décide de l'ordre de présentation des offres d'emploi. Il reçoit une pool de candidats présélectionnés par Elasticsearch (recherche sémantique) et applique un classement intelligent basé sur l'apprentissage des interactions utilisateurs passées.

**Métaphore** : Elasticsearch est le filtre grossier (élimine 99% des offres non pertinentes), le ranking ML est le joaillier qui trie les diamants par qualité.

---

## POURQUOI UN SERVICE SÉPARÉ

### Alternative Rejetée : Ranking Direct dans Elasticsearch
Elasticsearch propose des fonctions de scoring personnalisées (Function Score Query, Script Score).

**Limites d'Elasticsearch** :
1. **Pas de Learning-to-Rank natif** : Scoring basé sur TF-IDF/BM25, pas sur données comportementales
2. **Pas d'optimisation NDCG** : Impossible d'optimiser directement pour la qualité du classement global
3. **Feature engineering limité** : Difficile de combiner features hétérogènes (textuelles, numériques, temporelles)

**Avantages Service Séparé** :
- Utilisation de LightGBM avec objectif LambdaRank
- Entraînement offline sur données PostgreSQL
- Évolution indépendante du modèle sans toucher l'index Elasticsearch

---

## FLUX DE TRAITEMENT

### Étape 1 : Calcul du Top-K Dynamique
**Problème** : Si base contient 10 000 offres, analyser toutes est coûteux. Si base contient 50 offres, top-k fixe à 200 est absurde.

**Solution Adaptative** :
```
top_k = min(topk_max, max(topk_min, total_offers * topk_ratio))
```

**Exemple** :
- 10 000 offres → top_k = 200 (10% de 10k = 1000, plafonné à 200)
- 300 offres → top_k = 50 (10% de 300 = 30, relevé au minimum 50)

**Justification** : Balance entre couverture (ne pas manquer le meilleur candidat) et performance (limiter le calcul de features).

### Étape 2 : Feature Engineering
Transformation de données brutes en 11 features numériques normalisées [0,1].

**Catégories de Features** :

#### A. Features Sémantiques (35%)
- `semantic_score` : Score de similarité cosinus Elasticsearch (déjà calculé)

#### B. Features de Compétences (25%)
- `skill_overlap` : Jaccard similarity entre compétences requises et possédées
  - Formule : |A ∩ B| / |A ∪ B|
  - Robuste aux synonymes si skills normalisés en amont

#### C. Features d'Expérience (15%)
- `experience_match` : Ratio années expérience CV / années requises
  - <1.0 : Sous-qualifié (pénalité linéaire)
  - 1.0-1.5 : Match parfait
  - >1.5 : Sur-qualifié (pénalité modérée)

#### D. Features Contextuelles (25%)
- `seniority_match` : Alignement niveau (junior/mid/senior/lead)
- `location_score` : Proximité géographique
- `remote_compatibility` : Adéquation préférence télétravail
- `offer_freshness` : Récence publication (favorise offres récentes)
- `company_reputation` : Score employeur (optionnel)
- `application_rate` : Taux de candidature (optionnel)
- `salary_match` : Écart avec attentes salariales (optionnel)
- `contract_type_match` : CDI/CDD/Freelance (optionnel)

**Gestion Données Manquantes** : Toutes les features optionnelles utilisent 0.5 (neutre) si données absentes. Le modèle apprend leur importance réelle lors de l'entraînement.

### Étape 3 : Prédiction ou Heuristique
**Si modèle entraîné** :
- Calcul scores LightGBM pour chaque candidat
- Normalisation dans [0,1]

**Si modèle non entraîné** :
- Scoring heuristique : somme pondérée des features
- Poids basés sur littérature académique (BM25F, Learning-to-Rank papers)

**Transparence** : Chaque recommandation indique `ranking_method: 'ml_model' | 'heuristic'` pour monitoring.

### Étape 4 : Seuil Adaptatif
**Problème** : Un seuil fixe (ex: score >0.6) peut éliminer trop de candidats (si tous faibles) ou en garder trop (si tous excellents).

**Solution** :
```
threshold = max(min_score, percentile_75_of_scores)
```

**Exemple** :
- Scores : [0.35, 0.42, 0.55, 0.63, 0.71, 0.78]
- P75 = 0.71
- Seuil = max(0.40, 0.71) = 0.71
- Retenus : [0.71, 0.78] (2 candidats)

**Justification** : Garde toujours le top 25% tout en éliminant les candidats sous le minimum absolu.

### Étape 5 : Diversification
**Problème** : Top 5 résultats peuvent être 5 variations du même poste (même entreprise, même ville).

**Solution** : Suppression des doublons similaires.
- Calcul de similarité Jaccard sur combinaison (job_title + company + location)
- Si similarité >85%, éliminer le candidat de rang inférieur

**Exemple** :
```
Rang 1: "Senior Python Dev - TechCorp Paris"
Rang 2: "Python Senior Developer - TechCorp Paris" (85% similaire → éliminé)
Rang 3: "Data Scientist - DataLab Lyon" (différent → gardé)
```

### Étape 6 : Limitation Finale
Retour de 5 à 20 recommandations maximum, même si plus de candidats passent les filtres.

**Justification Psychologique** : Au-delà de 20 choix, l'utilisateur souffre de paralysie décisionnelle (paradoxe du choix, Schwartz 2004).

---

## ENTRAÎNEMENT DU MODÈLE

### Objectif : Maximiser NDCG@10
**NDCG** (Normalized Discounted Cumulative Gain) mesure la qualité du classement en pénalisant davantage les erreurs en haut de liste.

**Formule** :
```
DCG@k = Σ(i=1→k) (2^rel_i - 1) / log2(i+1)
NDCG@k = DCG@k / IDCG@k
```

**Interprétation** :
- Position 1 très pertinente (rel=4) vaut plus que position 10 très pertinente
- NDCG=1.0 : Classement parfait
- NDCG=0.0 : Pire classement possible

### Labels de Relevance
Mapping interactions → scores [0-4] :
- **0 (Non pertinent)** : REJECT explicite
- **1 (Vu)** : VIEW sans interaction
- **2 (Intérêt faible)** : CLICK court (<10s)
- **3 (Intérêt fort)** : CLICK long (>10s) ou SHARE
- **4 (Très pertinent)** : APPLY ou SAVE

**Justification** : Échelle alignée avec critères NDCG académiques (TREC, LETOR datasets).

### Hyperparamètres Choisis
- `objective='lambdarank'` : Optimisation directe du classement
- `metric='ndcg'` : Évaluation sur métrique business
- `learning_rate=0.05` : Faible pour convergence stable avec petits datasets
- `n_estimators=100` : Compromis vitesse/performance (entraînement <2min)
- `num_leaves=31` : Complexité modérée (évite overfitting sur <1000 samples)

### Validation et Déploiement
1. **Split 80/20** : Entraînement sur 80%, validation sur 20%
2. **Early Stopping** : Arrêt si NDCG validation stagne 10 rounds
3. **Seuil Qualité** : Déploiement uniquement si NDCG@10 ≥ 0.65
4. **Rollback Automatique** : Restauration ancien modèle si nouveau sous-performe

---

## GARANTIES DE PERFORMANCE

### Latence Cible
- **Feature Extraction** : <50ms pour 200 candidats
- **ML Prediction** : <30ms (LightGBM très rapide)
- **Post-processing** : <20ms (tri, filtres)
- **Total** : <100ms (ranking seul, hors Elasticsearch)

### Scalabilité
- **1 000 offres** : top_k=100, latence ~80ms
- **100 000 offres** : top_k=200, latence ~110ms (presque linéaire)

**Bottleneck** : Feature extraction, pas prédiction ML. LightGBM scale à des millions de prédictions/seconde.

### Consommation Mémoire
- **Modèle LightGBM** : ~5 MB (100 arbres)
- **Features en mémoire** : ~200 KB pour 200 candidats
- **Total** : <10 MB par requête

---

## DÉCISIONS ARCHITECTURALES ROBUSTES

### 1. Séparation Ranking / Retrieval
**Alternative** : Tout dans Elasticsearch avec scripts Painless.
**Choix** : Service séparé.
**Raison** : Évolutivité (changer modèle sans réindexation), spécialisation (LightGBM meilleur que scripts ES).

### 2. Features Optionnelles Plutôt qu'Obligatoires
**Alternative** : Crash si `company_reputation` manquant.
**Choix** : Fallback 0.5 (neutre).
**Raison** : Robustesse (service survit aux données incomplètes), évolutivité (ajout features sans migration DB).

### 3. Seuil Dynamique Plutôt que Fixe
**Alternative** : Toujours retourner top 10.
**Choix** : Seuil adaptatif + diversité.
**Raison** : Qualité (évite recommandations médiocres), UX (diversité perçue comme plus pertinente).

### 4. Bootstrap Mode
**Alternative** : Attendre 100 vraies interactions avant activer ML.
**Choix** : Pseudo-labels dès le démarrage.
**Raison** : Time-to-value (ML actif dès J1), apprentissage continu (amélioration progressive).

---

## MÉTRIQUES DE MONITORING

### Métriques Technique
- `ranking_latency_ms` : Histogramme P50/P95/P99
- `model_score_distribution` : Distribution scores prédits (détection drift)
- `fallback_rate` : % requêtes utilisant heuristique vs ML

### Métriques Business
- `ndcg_online` : NDCG calculé sur interactions réelles post-déploiement
- `click_through_rate_top3` : % clics sur top 3 recommandations
- `application_rate` : % candidatures parmi recommandations vues

### Alertes
- NDCG <0.50 : Modèle dégradé, rollback immédiat
- Fallback rate >20% : Problème entraînement modèle
- Latency P95 >200ms : Investigation performance
