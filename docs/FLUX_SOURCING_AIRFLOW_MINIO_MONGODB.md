# Flux Sourcing -> Airflow -> MinIO -> Cleaning -> MongoDB

## 1. Objectif de ce document

Ce document explique, de manière technique mais présentable, le flux de collecte et de préparation des offres d'emploi dans TalentFlow, depuis la récupération des données jusqu'au stockage nettoyé dans MongoDB.

Le périmètre couvert ici est volontairement limité à :

1. le **sourcing** des offres,
2. le passage par **Kafka** et **Spark Structured Streaming**,
3. le stockage brut dans **MinIO**,
4. l'orchestration par **Airflow**,
5. le **data cleaning**,
6. le stockage final nettoyé dans **MongoDB**.

Ce document ne traite pas en détail la recherche vectorielle Qdrant ni la recommandation CV. Il s'arrête à la couche Silver.

---

## 2. Vue d'ensemble du flux

Le pipeline réel est le suivant :

1. **Job Sourcing** collecte des offres depuis des sites web et des APIs.
2. Les offres sont **normalisées** et **dédupliquées rapidement**.
3. Elles sont publiées dans **Kafka** sur un topic brut.
4. **Spark Structured Streaming** consomme ce topic et écrit chaque offre en JSON brut dans **MinIO Bronze**.
5. **Airflow** surveille ce flux et déclenche automatiquement le nettoyage.
6. **Data Cleaning** lit les objets Bronze, nettoie et enrichit les données.
7. Les documents propres sont enregistrés dans **MongoDB Silver**.
8. Une fois traités, les objets Bronze sont **archivés** puis **retirés** du bucket de travail.

En une phrase :

> Scrapy/API collectent, Kafka transporte, Spark dépose dans Bronze, Airflow déclenche, Cleaning nettoie, MongoDB conserve la donnée propre.

---

## 3. Composants et rôle exact de chacun

### 3.1 `job-sourcing`

Service principal de collecte.

Rôle :

1. lancer les spiders Scrapy,
2. lancer les collecteurs API,
3. normaliser les offres brutes,
4. dédupliquer rapidement,
5. publier les événements dans Kafka.

Fichiers clés :

1. `backend/job-sourcing/main.py`
2. `backend/job-sourcing/run_spider.py`
3. `backend/job-sourcing/api_sourcing/collector.py`
4. `backend/job-sourcing/core/autopilot_planner.py`
5. `backend/job-sourcing/core/minio_client.py`

### 3.2 `Kafka`

Kafka sert de **bus d'événements** entre la collecte et l'écriture dans le data lake.

Rôle :

1. découpler le scraping de l'écriture stockage,
2. absorber les pics de collecte,
3. permettre à Spark de consommer les offres sous forme de flux.

Topic principal :

1. `talentflow_jobs_raw`

### 3.3 `spark-streaming`

Spark Structured Streaming consomme le topic Kafka et écrit les données brutes dans MinIO.

Rôle :

1. lire les messages Kafka en streaming,
2. convertir chaque message en objet JSON brut,
3. écrire ces objets dans le bucket Bronze de MinIO.

Fichier clé :

1. `backend/spark-streaming/stream_to_minio.py`

### 3.4 `MinIO`

MinIO est utilisé comme **data lake objet**.

Rôle dans ce flux :

1. stocker la donnée **brute** dans Bronze,
2. servir de point de passage entre ingestion et nettoyage,
3. conserver une archive des objets déjà traités.

Buckets concernés :

1. `jobs-bronze` : bucket de travail Bronze
2. `talentflow-archive` : archive des objets traités

### 3.5 `Airflow`

Airflow orchestre automatiquement les tâches.

Rôle :

1. déclencher le sourcing,
2. vérifier si Bronze a reçu de nouveaux objets,
3. lancer le cleaning seulement si nécessaire,
4. déclencher ensuite la phase suivante de reindex si besoin.

Fichier clé :

1. `backend/orchestration/dags/talentflow_pipeline.py`

### 3.6 `data-cleaning`

Service de transformation Bronze -> Silver.

Rôle :

1. lire les objets JSON bruts dans MinIO,
2. nettoyer les textes,
3. normaliser les champs,
4. enrichir les données,
5. calculer qualité, fraîcheur et expiration,
6. stocker le document final propre dans MongoDB.

Fichiers clés :

1. `backend/data-cleaning/main.py`
2. `backend/data-cleaning/pipeline.py`
3. `backend/data-cleaning/core/post_processor.py`
4. `backend/data-cleaning/processors/quality_freshness.py`

### 3.7 `MongoDB`

MongoDB sert ici de **couche Silver**, c'est-à-dire la base de données des offres nettoyées et exploitables.

Rôle :

1. stocker les offres prêtes à être utilisées,
2. servir de source de vérité métier pour la recherche et la recommandation,
3. conserver les champs enrichis et calculés.

---

## 4. Étape 1 : comment les offres sont collectées

La collecte n'est pas un simple "crawler global". Elle repose sur deux familles de sources :

1. les **sources scraping**,
2. les **sources API**.

### 4.1 Sources scraping

Exemples :

1. ANPE Togo
2. Emploi.tg
3. Lucreatif
4. Wiijob

Chaque source importante dispose d'un spider dédié avec :

1. des sélecteurs,
2. un parser,
3. une logique source-spécifique.

Cela permet d'extraire correctement :

1. `title`
2. `description`
3. `location`
4. `contract_type`
5. `apply_url` / `apply_email`
6. dates si disponibles

### 4.2 Sources API

Exemples :

1. JSearch
2. Adzuna
3. RemoteOK
4. HackerNews Jobs
5. Remotive
6. Arbeitnow

Le collecteur central API est dans :

1. `backend/job-sourcing/api_sourcing/collector.py`

Les offres API suivent ensuite exactement le même pipeline que les offres scrapées.

### 4.3 Décision automatique des sources à lancer

Le système ne relance pas toutes les sources brutalement à chaque cycle.

Il utilise un **autopilot planner** :

1. il regarde la priorité de la source,
2. il regarde le temps écoulé depuis le dernier run,
3. il regarde la qualité des derniers résultats,
4. il applique un backoff en cas d'échecs répétés,
5. il choisit les sources qui sont "due".

Fichier clé :

1. `backend/job-sourcing/core/autopilot_planner.py`

### 4.4 Temporalité du sourcing

Il existe deux temporalités à distinguer :

1. **la fréquence du DAG Airflow**
2. **la fréquence effective par source**

Le DAG principal tourne toutes les **30 minutes**.

Mais une source n'est pas forcément relancée à chaque passage. Le planner applique des intervalles de base :

1. priorité haute : environ toutes les `8 heures`
2. priorité moyenne : environ toutes les `12 heures`
3. priorité basse : environ toutes les `24 heures`
4. priorité nightly : environ toutes les `24 heures`

Donc :

> Airflow vérifie souvent, mais le planner évite de scraper inutilement.

---

## 5. Étape 2 : normalisation et déduplication avant Kafka

Avant publication dans Kafka, chaque offre est déjà préparée.

### 5.1 Normalisation minimale

Le système harmonise les champs bruts pour leur donner une structure commune.

Exemples :

1. un même champ `location` pour toutes les sources,
2. un même champ `posted_date_iso`,
3. un même champ `deadline_iso`,
4. un même champ `apply_method`.

### 5.2 Déduplication rapide

Une déduplication rapide est effectuée via un fingerprint stocké dans Redis.

Objectif :

1. éviter de republier 10 fois la même offre,
2. limiter le bruit très tôt,
3. économiser les ressources du pipeline.

Cette déduplication précoce ne remplace pas la déduplication métier du cleaning, mais elle réduit déjà fortement les répétitions.

---

## 6. Étape 3 : publication dans Kafka

Une fois préparée, chaque offre devient un **événement brut** publié dans Kafka.

Pourquoi Kafka est utilisé ici :

1. pour découpler le scraping du stockage,
2. pour rendre le flux plus robuste,
3. pour accepter des volumes variables,
4. pour montrer une architecture Big Data de streaming cohérente.

Dans cette architecture, Kafka joue le rôle de **tampon transactionnel de flux**.

---

## 7. Étape 4 : Spark écrit dans MinIO Bronze

Spark Structured Streaming consomme le topic Kafka et écrit les messages dans MinIO.

### 7.1 Ce qui est écrit

Chaque offre est écrite sous forme de fichier JSON brut dans le bucket Bronze.

Format du nom d'objet :

1. `site/date/hash.json`

Exemple logique :

1. `emploi_tg/2026-03-07/abc123.json`

### 7.2 Pourquoi MinIO Bronze

MinIO Bronze sert à :

1. conserver la donnée brute telle qu'elle a été reçue,
2. séparer ingestion et nettoyage,
3. permettre de retraiter le pipeline si nécessaire,
4. garder une architecture de type data lake.

### 7.3 Point important à connaître

Dans le design actuel, le bucket Bronze sert aussi de **file de travail**.

Cela signifie :

1. les nouveaux objets arrivent dans Bronze,
2. le cleaning les lit,
3. après traitement, ils sont copiés dans une archive,
4. ils sont retirés du bucket Bronze si `DELETE_BRONZE_AFTER_ARCHIVE=true`.

Donc Bronze ne doit pas être présenté comme un stockage historique immuable permanent.  
Le stockage historique est assuré par l'archive.

---

## 8. Étape 5 : comment Airflow détecte qu'il faut nettoyer

Airflow ne lance pas le cleaning au hasard.

Le DAG principal suit une logique séquentielle.

### 8.1 Étapes Airflow

Le DAG `talentflow_pipeline` fait ceci :

1. prendre un snapshot du nombre d'objets Bronze avant ingestion,
2. déclencher le sourcing,
3. attendre que Spark écrive réellement de nouveaux objets dans Bronze,
4. comparer Bronze avant / Bronze après,
5. si le delta est positif, lancer le cleaning,
6. sinon, ne pas lancer inutilement le nettoyage.

### 8.2 La décision de cleaning

Le critère principal est :

1. `bronze_after > bronze_before`

Si aucun nouvel objet n'est visible, le nettoyage est sauté.

### 8.3 Pourquoi cette logique est bonne

Elle évite :

1. de relancer le cleaning en boucle sans nouvelle donnée,
2. de surcharger MongoDB,
3. de faire des reindex inutiles plus loin.

---

## 9. Étape 6 : ce que fait exactement le data cleaning

Le service `data-cleaning` lit les objets du bucket Bronze et applique plusieurs transformations.

### 9.1 Validation minimale

Une offre sans champ minimal utile, par exemple sans titre exploitable, peut être ignorée.

### 9.2 Nettoyage texte

Le service :

1. retire le bruit HTML,
2. normalise les espaces,
3. standardise certains champs comme `location` ou `contract_type`.

### 9.3 Normalisation source-spécifique

Des corrections par source sont ensuite appliquées pour :

1. réparer des titres cassés,
2. corriger des localisations,
3. éviter les faux champs métier,
4. remettre de la cohérence quand le DOM source est imparfait.

### 9.4 Déduplication

Une déduplication métier plus solide est appliquée.

Objectif :

1. ne conserver qu'une version utile d'une offre,
2. réduire les duplications inter-sources ou intra-source.

### 9.5 Enrichissement

Le cleaning enrichit ensuite le document avec :

1. compétences détectées,
2. soft skills,
3. expérience estimée,
4. niveau d'études estimé,
5. provider LLM utilisé si applicable.

Règle actuelle :

1. Mistral est le LLM principal du cleaning,
2. Qwen local est seulement un fallback optionnel,
3. sinon le système tombe sur NER + patterns.

### 9.6 Calcul qualité et fraîcheur

Le cleaning calcule aussi des champs métier essentiels :

1. `is_expired`
2. `is_stale`
3. `freshness_days`
4. `freshness_source`
5. `stale_reason`
6. `quality_score`
7. `title_confidence`
8. `location_confidence`
9. `date_confidence`
10. `apply_confidence`
11. `description_confidence`

Ces champs servent ensuite au ranking et à la recommandation.

---

## 10. Gestion des dates : publication, deadline, stale

Un point important à savoir en présentation :

> le système ne fabrique pas de fausses dates limites.

### 10.1 Si la deadline existe

Le pipeline :

1. normalise `deadline_iso`,
2. calcule `days_until_deadline`,
3. déduit `is_expired=true` si la deadline est passée.

### 10.2 Si la deadline n'existe pas

Le pipeline utilise un ordre de repli :

1. `posted_date_iso`
2. sinon `scraped_at`

Puis il calcule une fraîcheur relative :

1. `freshness_days`
2. `is_stale`

### 10.3 Pourquoi c'est important

Beaucoup d'APIs et de sites n'exposent pas de vraie deadline.

Il faut donc distinguer :

1. **expiration vraie** si deadline connue,
2. **obsolescence probable** si la date est absente et que l'offre est trop ancienne.

---

## 11. Étape 7 : stockage dans MongoDB Silver

Après nettoyage, le document final est enregistré dans MongoDB.

MongoDB Silver contient :

1. les champs métier nettoyés,
2. les champs enrichis,
3. les champs qualité,
4. les signaux de fraîcheur,
5. les métadonnées de traitement.

En pratique, MongoDB Silver est la **base de données propre et exploitable** du système.

Elle alimente ensuite :

1. la recherche,
2. la recommandation,
3. le dashboard.

---

## 12. Étape 8 : post-traitement Bronze après cleaning

Une fois les objets traités :

1. ils sont copiés dans le bucket `talentflow-archive`,
2. ils sont supprimés du bucket Bronze si la politique active l'autorise.

Fichier responsable :

1. `backend/data-cleaning/core/post_processor.py`

### Pourquoi ce mécanisme existe

Il permet :

1. de garder Bronze comme file de travail,
2. d'éviter de retraiter les mêmes objets à chaque cycle,
3. de conserver une archive brute si on veut auditer ou retraiter plus tard.

---

## 13. Temporalités réelles du flux

### 13.1 Fréquence du DAG principal

Le DAG principal tourne :

1. toutes les `30 minutes`

### 13.2 Fréquence réelle de sourcing

Le sourcing effectif dépend :

1. de la priorité de la source,
2. du temps depuis le dernier run,
3. de la qualité des derniers résultats,
4. des éventuels échecs récents.

### 13.3 Déclenchement du cleaning

Le cleaning n'est lancé que si Bronze a reçu de nouveaux objets.

### 13.4 Déclenchement du reindex

Le reindex n'est lancé que si :

1. le cleaning a produit de nouvelles données,
2. ou si le moteur de recherche détecte une dérive.

---

## 14. Ce qu'il faut dire à l'oral en une version simple

Version courte et solide :

> Nous avons conçu un pipeline Big Data automatisé. Les offres sont d'abord collectées par des spiders Scrapy et des connecteurs API. Elles sont ensuite publiées dans Kafka. Spark Structured Streaming consomme ces événements et écrit chaque offre brute dans MinIO Bronze sous forme de JSON. Airflow orchestre ensuite le cycle : il vérifie qu'il y a bien de nouveaux objets dans Bronze, puis lance le data cleaning. Le cleaning lit les objets, nettoie les textes, normalise les champs, enrichit les compétences, calcule la qualité et la fraîcheur, puis stocke le résultat propre dans MongoDB Silver. Une fois traité, l'objet brut est archivé pour éviter les retraitements inutiles.

---

## 15. Ce qu'il ne faut pas dire

Éviter ces formulations imprécises :

1. "Airflow scrape directement les sites"
   - Faux : Airflow orchestre, mais ne scrape pas lui-même.

2. "MinIO Bronze est la base finale"
   - Faux : Bronze stocke la donnée brute, Silver Mongo stocke la donnée exploitable.

3. "Le cleaning tourne tout le temps sans condition"
   - Faux : il est conditionné à la présence de nouvelles données Bronze.

4. "Toutes les dates sont exactes"
   - Faux : certaines sont vraies deadlines, d'autres sont des dates de publication ou des proxys de fraîcheur.

5. "Le système ajoute des deadlines manquantes"
   - Faux : il calcule la fraîcheur, il n'invente pas une deadline.

---

## 16. Forces de cette architecture

### 16.1 Ce qu'elle montre bien pédagogiquement

Cette architecture démontre concrètement :

1. le scraping multi-sources,
2. l'ingestion temps réel,
3. le data lake Bronze,
4. l'orchestration par DAG,
5. la transformation Silver,
6. la séparation claire entre brut et propre.

### 16.2 Ce qu'elle apporte techniquement

Elle permet :

1. un pipeline découplé,
2. des traitements relançables,
3. une meilleure observabilité,
4. une montée en charge plus propre qu'un scraping monolithique.

---

## 17. Limites actuelles à assumer proprement

Pour rester crédible, il faut aussi connaître les limites.

### 17.1 Ajout d'une nouvelle source

Une nouvelle source n'est pas absorbée magiquement.

Il faut au moins :

1. l'ajouter au registre,
2. définir ses paramètres,
3. éventuellement lui donner un parser dédié.

### 17.2 Les sources n'ont pas toutes la même qualité

Certaines sources fournissent :

1. de vraies deadlines,
2. des liens de candidature propres,
3. des localisations précises.

D'autres non.  
Le cleaning corrige beaucoup, mais pas tout parfaitement.

### 17.3 Bronze est un bucket de travail

Dans l'état actuel du projet :

1. Bronze n'est pas un entrepôt historique infini,
2. l'archive est la couche de conservation brute après traitement.

---

## 18. Fichiers à citer si on te demande “où c'est dans le code ?”

1. orchestration du pipeline :
   - `backend/orchestration/dags/talentflow_pipeline.py`
2. API de collecte :
   - `backend/job-sourcing/main.py`
3. sélection automatique des sources :
   - `backend/job-sourcing/core/autopilot_planner.py`
4. collecte API :
   - `backend/job-sourcing/api_sourcing/collector.py`
5. écriture dans Bronze :
   - `backend/spark-streaming/stream_to_minio.py`
6. lecture Bronze + cleaning :
   - `backend/data-cleaning/pipeline.py`
7. post-traitement Bronze / archive :
   - `backend/data-cleaning/core/post_processor.py`

---

## 19. Résumé final

Le flux métier présenté dans ce projet est cohérent et défendable :

1. **collecte** multi-sources,
2. **transport** par Kafka,
3. **atterrissage brut** dans MinIO Bronze via Spark,
4. **détection automatique** par Airflow,
5. **nettoyage/enrichissement** dans le service `data-cleaning`,
6. **stockage propre** dans MongoDB Silver,
7. **archivage** des objets bruts traités.

Autrement dit :

> le système sépare correctement l'acquisition, le transit, le stockage brut, l'orchestration et la préparation métier des offres.

