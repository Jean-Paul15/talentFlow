# SERVICE DE GESTION DU CACHE - ANALYSE APPROFONDIE

## JUSTIFICATION ÉCONOMIQUE

### Coût Sans Cache
**Scénario Utilisateur Typique** :
1. Recherche initiale : "Data Scientist Paris" → 210ms
2. Ajout filtre salaire : "≥50K EUR" → 210ms (recalcul complet)
3. Ajout filtre remote : "Hybrid" → 210ms (recalcul complet)
4. Retour arrière : Suppression filtre remote → 210ms (recalcul complet)

**Total** : 840ms perçus, 4× calculs identiques (embedding pas changé).

### Gain Avec Cache
**Mêmes Actions** :
1. Recherche initiale : 210ms (MISS cache, calcul + mise en cache)
2. Filtre salaire : 15ms (HIT cache embedding + nouveau ranking)
3. Filtre remote : 15ms (HIT cache embedding)
4. Retour arrière : 15ms (HIT cache recommandations complètes)

**Total** : 255ms perçus, gain 70%.

---

## ARCHITECTURE TROIS NIVEAUX

### Niveau 1 : Cache Embeddings (Le Plus Coûteux)

#### Motivation
Calcul embedding = Opération la plus lente :
- Tokenization : 2000 mots CV → 300 tokens
- Forward pass modèle multilingual-MiniLM : 768-dim tensor
- GPU : 50ms | CPU : 750ms

**Observation** : CV change rarement pendant une session (20-30 min).

#### Stratégie
**Clé** : Hash du texte CV (premiers 1000 caractères).
```
key = f"emb:{sha256(cv_text[:1000]).encode()}.hexdigest()}"
```

**Pourquoi 1000 chars** : 
- Capture titre + résumé + début expériences
- Balance unicité (évite collisions) / coût hash (rapide)

**Valeur** : Array NumPy sérialisé (pickle) → 3 KB.

**TTL** : 3600 secondes (1 heure).
**Justification** :
- Session utilisateur moyenne : 15-20 min
- TTL 1h couvre 3-4 sessions consécutives
- Au-delà, risque staleness (utilisateur a pu modifier CV)

#### Invalidation
**Trigger** : Endpoint `/api/cv/update` appelé.
**Action** :
```
redis.delete(f"emb:{cv_id}")  # Suppression proactive
```

**Cas Particulier** : Si utilisateur modifie CV pendant recherche.
**Solution** : Inclure hash dans clé (auto-invalidation si texte change).

### Niveau 2 : Cache Recommandations (Le Plus Réutilisé)

#### Motivation
Filtres appliqués sur mêmes résultats Elasticsearch :
- Utilisateur affine salaire : 45K → 50K → 55K
- Même pool de candidats, filtrage différent
- Évite requête ES (100ms) + ranking ML (20ms)

#### Stratégie
**Clé** : Hash (cv_id + filters_sorted + model_version).
```
filters_str = json.dumps(sorted(filters.items()))
key = f"rec:{hashlib.md5(f'{cv_id}{filters_str}{model_version}'.encode()).hexdigest()}"
```

**Pourquoi model_version** : 
- Si modèle réentraîné, invalidation automatique (clé change)
- Pas besoin FLUSHDB manuel

**Valeur** : Liste job_ids + scores + metadata (JSON) → ~5 KB.

**TTL** : 600 secondes (10 minutes).
**Justification** :
- Offres publiées en temps réel (fraîcheur importante)
- 10 min = compromis UX (pas de staleness perçue)

#### Invalidation
**Triggers** :
1. **Nouvelle offre publiée** : `redis.delete('rec:*')` via pattern (costaud mais rare)
2. **Modèle ML réentraîné** : model_version increment → clés invalides naturellement
3. **TTL expire** : Automatique

**Optimisation** : Pub/Sub Redis.
```
# Publisher (service ingestion offres)
redis.publish('jobs_updated', 'new_offer_123')

# Subscriber (service recommendation)
def on_message(message):
    redis.delete('rec:*')  # Invalidation sélective possible
```

### Niveau 3 : Cache Métadonnées Jobs (Le Plus Stable)

#### Motivation
Détails offre rarement modifiés après publication :
- Titre, description, salaire, compétences requises
- Requêtes GET Elasticsearch répétées inutilement

#### Stratégie
**Clé** : ID offre directement.
```
key = f"job:{job_id}"
```

**Valeur** : Document complet (JSON) → 2 KB.

**TTL** : 86400 secondes (24 heures).
**Justification** :
- Offres rarement éditées après publication
- 24h = balance fraîcheur / hit rate
- Si édition, invalidation manuelle possible

#### Invalidation
**Trigger** : Endpoint `/api/jobs/{job_id}` PATCH appelé.
**Action** :
```
redis.delete(f"job:{job_id}")
```

---

## PATTERNS D'IMPLÉMENTATION

### Cache-Aside (Lazy Loading)

#### Principe
Application contrôle explicitement le cache :
1. Vérifier cache (GET)
2. Si HIT → Retourner
3. Si MISS → Calculer + Mettre en cache (SET) + Retourner

#### Avantages
- Simplicité implémentation
- Résilience (si Redis down, calcul direct)
- Pas de pré-chargement complexe

#### Code Pattern
```python
def get_embedding_with_cache(cv_text, redis_client, model):
    key = generate_cache_key(cv_text)
    
    try:
        cached = redis_client.get(key)
        if cached:
            return deserialize(cached)
    except RedisError as e:
        logger.warning(f"Cache unavailable: {e}")
    
    # Cache MISS ou Redis down
    embedding = model.encode(cv_text)
    
    try:
        redis_client.setex(key, 3600, serialize(embedding))
    except RedisError:
        pass  # Pas critique si mise en cache échoue
    
    return embedding
```

### Cache Stampede Protection

#### Problème
Scénario : Clé populaire expire, 100 requêtes simultanées la recalculent.
**Impact** : Surcharge GPU/CPU, latence multipliée.

#### Solution : Distributed Lock
```python
import redis.lock

def get_with_lock(key, compute_fn, redis_client, ttl=3600):
    # Tentative cache hit
    cached = redis_client.get(key)
    if cached:
        return deserialize(cached)
    
    # Acquérir lock distribué
    lock = redis.lock.Lock(redis_client, f"lock:{key}", timeout=10)
    
    if lock.acquire(blocking=False):
        try:
            # Double-check après acquisition (un autre thread a pu calculer)
            cached = redis_client.get(key)
            if cached:
                return deserialize(cached)
            
            # Calcul protégé
            result = compute_fn()
            redis_client.setex(key, ttl, serialize(result))
            return result
        finally:
            lock.release()
    else:
        # Un autre thread calcule, attendre et retry
        time.sleep(0.1)
        return get_with_lock(key, compute_fn, redis_client, ttl)
```

**Garantie** : Un seul thread calcule, les autres attendent.

---

## SÉRIALISATION ET COMPRESSION

### Formats de Sérialisation

#### Embeddings (NumPy Arrays)
**Option 1** : Pickle (choisi).
- **Avantages** : Simple, natif Python.
- **Inconvénients** : Pas cross-language, taille non optimale.

**Option 2** : MessagePack.
- **Avantages** : Compact, rapide.
- **Inconvénients** : Nécessite bibliothèque tierce.

**Option 3** : Protobuf.
- **Avantages** : Schema strict, cross-language.
- **Inconvénients** : Overhead définition schema.

**Choix** : Pickle pour simplicité, évolution vers MessagePack si nécessaire.

#### Recommandations (Dictionnaires)
**Format** : JSON.
**Justification** : Lisible (debug), standard, sérialisation native Python.

### Compression

#### Motivation
- Embedding 768 float32 = 3072 bytes
- JSON recommandations = 5000 bytes
- Redis stockage mémoire (coûteux)

#### Stratégie
**LZ4** : Compression ultra-rapide.
- Ratio compression : 2-3× pour JSON
- Latency overhead : +1ms (négligeable)

**Code** :
```python
import lz4.frame

def set_compressed(redis_client, key, value, ttl):
    serialized = json.dumps(value).encode()
    compressed = lz4.frame.compress(serialized)
    redis_client.setex(key, ttl, compressed)

def get_compressed(redis_client, key):
    compressed = redis_client.get(key)
    if not compressed:
        return None
    decompressed = lz4.frame.decompress(compressed)
    return json.loads(decompressed)
```

**Gain** : Économie 50% mémoire Redis (critique si millions de clés).

---

## MONITORING ET OBSERVABILITÉ

### Métriques Clés

#### Hit Rate par Niveau
```
cache_hit_rate_embeddings = hits / (hits + misses)
cache_hit_rate_recommendations = hits / (hits + misses)
```

**Targets** :
- Embeddings : >70% (utilisateurs reviennent souvent)
- Recommandations : >50% (filtres variés)

#### Latency Distribution
```
latency_with_cache_ms (histogram)
latency_without_cache_ms (histogram)
```

**Analyse** : P95 latency doit être <100ms avec cache.

#### Memory Usage
```
redis_memory_used_bytes
redis_memory_max_bytes
redis_memory_fragmentation_ratio
```

**Alerte** : Si >80% capacité → Scale-up Redis.

#### Eviction Rate
```
redis_evicted_keys_total
```

**Interprétation** :
- 0 : Excellent (mémoire suffisante)
- >1% : Préoccupant (TTL trop longs ou mémoire insuffisante)

### Dashboards Grafana

#### Panel 1 : Hit Rate Timeline
Graphique ligne avec 2 séries :
- Embeddings hit rate (vert)
- Recommendations hit rate (bleu)

**Insight** : Détection dégradation (ex: après deploy nouveau modèle).

#### Panel 2 : Cache Latency vs Direct
Histogrammes superposés :
- Latency cache HIT (vert, P50/P95/P99)
- Latency cache MISS (rouge, P50/P95/P99)

**Insight** : Quantification gain performance.

#### Panel 3 : Redis Memory
Gauge avec seuils :
- <50% : Vert (sain)
- 50-80% : Jaune (surveillance)
- >80% : Rouge (action requise)

### Alertes PrometheusRule

#### Alerte 1 : Hit Rate Bas
```yaml
- alert: CacheHitRateLow
  expr: cache_hit_rate_embeddings < 0.5
  for: 10m
  annotations:
    summary: "Cache hit rate embedding <50% pendant 10min"
    description: "Vérifier TTL, patterns utilisateurs, Redis disponibilité"
```

#### Alerte 2 : Mémoire Redis Critique
```yaml
- alert: RedisMemoryCritical
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
  for: 5m
  annotations:
    summary: "Redis mémoire >90%"
    description: "Scale-up immédiat ou réduire TTL"
```

---

## TESTS DE CHARGE

### Scénario 1 : Cache Cold
**Setup** : Redis vide (FLUSHDB).
**Charge** : 1000 req/s pendant 1 min.
**Attente** :
- Hit rate : 0% (toutes MISS)
- Latency P95 : ~300ms (calculs directs)
- Redis memory : Croissance linéaire jusqu'à stabilisation

### Scénario 2 : Cache Warm
**Setup** : Redis pré-chargé (simule trafic normal).
**Charge** : 1000 req/s pendant 5 min.
**Attente** :
- Hit rate : >60% après 2 min
- Latency P95 : <100ms
- Redis memory : Stable (évictions balancent insertions)

### Scénario 3 : Stampede Test
**Setup** : Clé populaire expire, burst 500 req simultanées.
**Sans Lock** : 500 calculs parallèles (surcharge GPU).
**Avec Lock** : 1 calcul, 499 attentes (performant).

---

## ÉVOLUTIONS FUTURES

### Cache Prédictif
**Idée** : Pré-calculer embeddings pour utilisateurs fréquents.
**Implémentation** : Cronjob 3h du matin.
```python
# Identifier top 100 CVs consultés dernières 24h
top_cvs = query_most_viewed_cvs(limit=100)

# Pré-calculer et cacher
for cv in top_cvs:
    embedding = model.encode(cv.text)
    redis.setex(f"emb:{cv.id}", 86400, serialize(embedding))
```

**Gain** : Hit rate 95% pour utilisateurs récurrents.

### Cache Multi-Région
**Problème** : Service déployé Europe + Afrique, latency Redis cross-region.
**Solution** : Redis Cluster avec réplication.
- Write : Master (région primaire)
- Read : Replicas locaux (faible latence)

**Trade-off** : Eventual consistency (acceptable pour cache).

### Adaptive TTL
**Idée** : TTL dynamique basé sur patterns.
**Logique** :
```python
if cv_last_modified < 7_days_ago:
    ttl = 86400  # Stable, TTL long
else:
    ttl = 3600  # Récent, TTL court (peut changer)
```

**Gain** : Optimise mémoire sans sacrifier fraîcheur.

---

## DÉCISIONS ARCHITECTURALES ROBUSTES

### 1. Redis Plutôt que Memcached
**Memcached** : Plus simple, léger.
**Redis** : Structures avancées (Sets pour patterns), persistence, pub/sub.
**Choix** : Redis pour évolutivité (futurs use cases: sessions, leaderboards).

### 2. Cache Optionnel, Pas Obligatoire
**Philosophie** : Service fonctionne même si Redis down.
**Implémentation** : Tous appels Redis dans try/except, fallback calcul direct.

### 3. Invalidation Totale vs Sélective
**Nouveau job publié** : Invalider tous `rec:*` (simple) vs seulement caches concernés (complexe).
**Choix** : Invalidation totale pour éviter bugs, coût acceptable (reconstruction 10 min).

### 4. Compression LZ4 Systématique
**Alternative** : Pas de compression (simplicité).
**Problème** : Coût mémoire Redis élevé.
**Choix** : LZ4 par défaut, +1ms latency acceptable pour 50% économie mémoire.
