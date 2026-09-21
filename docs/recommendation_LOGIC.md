# LOGIQUE DU SYSTEME DE RECOMMANDATION (RECOMMENDATION)

Ce document explique de A a Z et de maniere exhaustive, le fonctionnement complet du moteur hybride de recommandation d'offres d'emploi (Job Matching). Ce document alterne volontairement entre la vulgarisation pour comprendre les concepts "non-techniques" (l'informatique pour les debutants), jusqu'aux details architecturaux ultra-pointus (formules algebriques, Machine Learning, MLOps, Caching Redis) exploites en arriere-plan par le backend TalentFlow.

La promesse et l'algorithme "recommandation" ici ne se basent pas sur une serie de filtres arbitraires de bases de donnees (ex: `SELECT * FROM jobs WHERE skill='Python'`). L'algorithme repose sur le NLP (Traitement Automatique du Langage Naturel), les espaces vectoriels (Algebre Lineaire), un modele lambda de Machine Learning LambdaRank, L'hyper-personalisation via IA Generative (LLM), et une Infrastructure d'Apprentissage Continu (Active Learning / Tracking Loop).

---

## 1. INTRODUCTION ET ARCHITECTURE MULTI-ETAGES (PIPELINE)

### 1.1. Philosophie du Matching Sémantique
Imaginez que vous vouliez recruter un "Spécialiste de la Sécurité Informatique". Un candidat inscrit sur son CV : "Expertise en protection des réseaux, gestion d'incidents et cryptographie depuis 5 ans".
- **L'informatique d'hier** dirait : Le candidat n'a pas ecrit "Spécialiste de la Sécurité Informatique", donc le score est de 0%. L'offre est cachée.
- **L'informatique de TalentFlow** (l'algorithme) calcule que "protection des réseaux" est mathematiquement synonyme de "Securite". L'offre est classee avec 90% de pertinence, meme si les mots exacts different.

Mais le "sens" ne suffit pas. Parfois on **veut** absolument que le candidat connaisse ReactJS, et on ne veut pas qu'on lui propose l'apprentissage de VueJS (qui a un sens proche). C'est pourquoi TalentFlow utilise une orchestration **Hybride**.

### 1.2. Orchestration Technique de la Pipeline
L'ensemble de ce systeme de recommandation suit une chaine stricte situee techniquement dans le fichier racine `backend/recommendation/src/services/matching_pipeline.py` :
1. **Extraction de Connaissance & Vectorisation** : Transformer texte en nombres (Vecteurs) au moyen d'un Embedder local.
2. **Recherche Vectorielle Hybride et Fusion RRF** : Interrogation haute-frequence sur Qdrant.
3. **Re-Ranking as Code (Machine Learning)** : Recalcul algorithmique par `LightGBM` optimisant des variables Business.
4. **Appel LLM avec Fallback pour Explicabilite** : Generation de conseils (Prompt JSON format avec Gemini/DeepSeek).
5. **Suivi des Interactions et Reflexion par Airflow** : Capture asynchrone des actions Flutter (clic/view) pour retroagir et corriger les calculs du Machine Learning au fil des jours.

---

## 2. ETAPE 1 : PREPARATION DES VECTEURS (EMBEDDING SERVICE)

Le `EmbeddingService` traduit un document litteraire (Francais/Anglais) en une adresse dans un univers mathematique.

### 2.1. Sentence Transformers et FastEmbed
Les modeles de NLP de type BERT (Architecture Transformers) generent de l'attention multi-tete (Self-Attention) pour cerner le contexte des mots du texte (Offre d'emploi ou Résumé CV). L'embedding reduit ensuite cette connaissance en un vecteur Dense de N dimensions.

Dans TalentFlow, le `EmbeddingService` (`backend/recommendation/services/embedding_service.py`) fonctionne avec une double strategie de survie :
- Il tente d'abord de charger **FastEmbed** (`backend="fastembed"`), qui effectue les calculs de vecteurs sans charger massivement le proc GPU ou la librairie lourde PyTorch (`cache_dir="/opt/fastembed-cache"`).
- S'il echoue, il lance le "Fallback" classique (`backend="sentence-transformers"`).

### 2.2. La Structure du Vecteur
Pour une offre d'emploi, $V_{offre} = [v_1, v_2, ..., v_{384}]$ (exemple d'un vecteur a 384 dimensions).
Dans le graphe multidimensionnel, tous les metiers lies a la "Finance" pointent vers un cluster stellaire, tous les postes en "Sante" vers un autre.

### 2.3. Gestion du Cache Embedding (Redis)
Pour eviter de griller des centaines de Watts a refaire la meme traduction vectorielle a chaque frappe clavier, TalentFlow utilise l'optimisation `CVCacheManager` avec REDIS (`backend/recommendation/src/shared/cache_manager.py`). 
Le hash d'un CV (`hashlib.sha256`) se transforme en clef unique (`key = f"emb:{sha...}"`). Redis le stocke 3600 secondes. Prochain appel ? Latence < 5ms. Hit de memoire evitant le recours au processeur IA.

---

## 3. ETAPE 2 : ANALYSE ET DECOMPOSITION DU CV CANDIDAT

### 3.1. Parsing et "Denoising" du CV
L'utilisateur final uploade via l'App Flutter son CV (Souvent un PDF). Il est traite par l'API `cv_text`. 
- Les bruits visuels (Tabulations multiples, retours à la ligne illogiques, headers) sont normalisés via Expressions Regulieres (Regex).
- Notre dictionnaire `_ROLE_HINTS_BY_SKILL` associe certaines listes extraites. S'il lit au hasard {"spark", "kafka", "airflow"}, il enregistre sous la constante "data engineering, etl".
  
### 3.2. Construction du CVAnalysisResult
Le profil se numerise autour de piliers certifiés :
- **Skills** : Les technologies pures trouvées (`python`, `sql`, `react`), classées en minuscules.
- **Experience Years** : Logique deduite des dates.
- **Education** : Analyse sémantique des Master/Licence.

Ce super-paragraphe canonique "nettoyé" passe au tour de l'EmbeddingService de l'Etape 2. Il en resort le fameux Vecteur Candidat : $V_{cv}$.

---

## 4. ETAPE 3 : LA RECHERCHE HYBRIDE PAR QDRANT ET LA FUSION RRF

La methode de recherche s'eloigne entierement de ELASTICSEARCH/SQL pour s'ancrer dans l'espace Vectoriel via la base **QDRANT**. (Le moteur ultra-rapide en Rust dédié).

### 4.1. Recherche Dense (Similarité Sémantique Cosinus)
Le pipeline de matching vectorise le CV. La recherche Cosinus, définie mathematiquement par :
$Score_{cosinus}(V_{cv}, V_{offre}) = \frac{V_{cv} \cdot V_{offre}}{||V_{cv}|| ||V_{offre}||}$
Ce score mesure l'angle entre les deux vecteurs. Un vecteur CV de DataScientist, très proche en angle d'une offre DataAnalyst, donnera $\approx 0.89$. Le profil aura une pertinence sémantique tres elevee.

### 4.2. Recherche Sparse (BM25 - Recherche Lexicale de précision)
Mais la Sémantique est lache. Un développeur FrontEnd Vue.Js n'est pas forcement recruté si le client stipule STRICTEMENT « React ». 
Le backend exécute donc en simultané sur Qdrant une recherche "Sparse" (Mots-cles ponderes type BM25). Si le mot rare "Flutter" figure à la fois sur le CV et l'offre, la sparse lui attribue des extremums locaux inateigniables par la vectorisation dense classique.

### 4.3. L'algorithme de regularisation : Reciprocal Rank Fusion (RRF)
Dans `search_service_parts/backend_impl.py`, les resultats asymetriques se fondent selon l'equation RRF proposee par Cormack et al. :
$Score_{RRF} = \frac{1}{k + Rang_{Dense}} + \frac{1}{k + Rang_{Sparse}}$
Avec $k$ calibré à 60 (hyperparametre issu des standards scientifiques). 
Ainsi, un poste classé 2ème par le Sens (Dense) et 15ème par le Mot-Clé (Sparse) dominera un poste classé 1er en Sens (1/61 = 0.0163) mais 5000ème en Mots-Clé. 

Cette orchestration ramène un Pool Brut Optimal contenant entre 100 et 200 candidats ($pool\_size$).

---

## 5. ETAPE 4 : INTELLIGENCE ARTIFICIELLE METIER (LE RERANKING MACHINE LEARNING)

Qdrant nous fournit 200 "bonnes" offres, mais sans ame RH. Le `MLRankingService` (dans `ranker_core.py`) filtre et ordonne avec l'algorithme des arbres de décisions : **LightGBM**.

### 5.1. Extraction des Features Structurées (Les Critères Mathématiques)
Chaque offre du Pool Brut est découpée en 10 dimensions d'analyse par rapport au CV :
1. `skills_overlap_ratio` : La fraction de superposition exacte (Intersection Set theory).
2. `experience_match` : Fonction punitive (Decay). Si l'offre necessite 5 ans d'expérience et le candidat détient 2 ans, le feature tombe à zéro de façon asymetrique.
3. `days_since_posted` : Pour favoriser les annonces d'emploi frâiches de quelques semaines, limitant la candidature aux offres fantômes.
4. `semantic_similarity` : La fusion brute conservée pour l'Arbre Gradient (Le score Qdrant).
5. Et autres features : Pénibilité géographique, Score entreprise, Concordance Salariale.

### 5.2. Lambdarank & Optimisation de la Metric NDCG
L'entrainement LightGBM (Gradient Boosting Trees) n'est pas arbitraire. Il se définit avec `objective='lambdarank'`.
Le score ne vise pas à estimer le pourcentage de match à la décimale près. Il s'interdit d'être moyen ! Il cherche à maximiser le **NDCG@10**. 
Le principe du Normalized Discounted Cumulative Gain force le classificateur à placer les offres les "plus parfaites" exclusivement au Top 1 à Top 5, car un candidat ne dépassera psychologiquement jamais le Scroll (defilement index) de sa Page de Dashboard Mobile. Les arbres sont créés en observant des paires.

### 5.3. Architecture Heuristique (Fallback Systematique)
Un systeme critique ne doit jamais planter si le cluster d'entrainement corrompt le `.pkl`.
Dans le code `ranker_core.py` :
```python
if self.is_trained:  # Verifie si le modele ML validé est pre-chargé. MLOPS valide.
    scores = predict_scores(...) 
else:
    scores = rule_based_scoring(...) # Le Fallback de Secours
```
L'algorithme bascule en un clic sur une Equation Determinisite Statistique (Heuristique / Pondération Humaine à valeurs académiques certifiées) en moins d'une milliseconde pour garantir un Uptime de 99.999%.

---

## 6. ETAPE 5 : L'EXPLICABILITE (LARGE LANGUAGE MODEL & FALLBACKS)

Fournir le tri n'est plus suffisant en 2026. L'utilisateur reclame le "Coaching". Le pipeline active `orchestrator_recommend.py`.

### 6.1. Le RAG (Retrieval-Augmented Generation) 
TalentFlow passe les 5 offres phares ($job_{1...5}$) et l'entiereté du CV à l'IA Générative Gemini (Prompt Structure).
On intime à l'API Generative Google/OpenAI le respect implacable d'un Schéma JSON ($100\%$ structuré). 
Les champs :
- `profileSummary` : Un recap de qui est le Candidat.
- `strengths` : De "Ce que l'algorithme a estimé Bon" (traduit en mots flatteurs compréhensibles par l'étudiant).
- `gaps` (ou missingKeywords) : Le cruel décalage de son Curriculum avec les offres cibles, pointant les technologies/certifications manquantes.
- `offerPlaybooks` : Pour CHAQUE offre, l'IA génère en JSON ("targetSummary", "rewrite") un tutoriel chirurgical proposant au TalentFlow la "refonte de sa propre expérience" pour matcher le système ATS de l'employeur.

### 6.2. La Redondance Deepseek API 
Gérer un LLM est sujet à la perte reseau ou Rate Limit. L'infrastructure est protégé.
Si le `quality_gate` ou si un echec timeout API survient, TalentFlow bascule instantanément sur un modele Cloud `Deepseek Fallback`. Moins couteux et tres efficace en Parsing JSON, ce systeme garantie que l'interface Flutter du front reçoit TOUJOURS une donnée correcte structurellement sur le fil de l'internet.

### 6.3. Cache LLM Redis
De meme que pour les $Vectors$, toutes ces opérations LLM (facturées au token) sont "hashées" via un calcul complexe entre le hash du CV et une liste concaténée ("|") des Identifiants d'Offres (cf. `api/cv_text/cache.py`). 
Le tout est posé sur Redis : Un utilisateur qui f5 (rafraîchit) l'ecran mobile verra la structure pop-up de son coaching en quelques microsecondes (Hit cache JSON), épargnant l'appel de 4 secondes vers Gemini.

---

## 7. ETAPE 6 : EXPERIENCE FRONTEND DANS L'UI (FLUTTER)

L'ensemble des recommandations transite par l'API-Gateway via le langage strict GRAPHQL (Query Typed).
L'écran final Flutter (`CvResultInsightsPanel`) ingère les `playbooks` et la `cvAnalysis`.
1. **Révélation Séquentielle** : Les forces sortent en premier bloc pour retenir l'attention positive de l'humain.
2. **Pédagogie d'Action** : Les Gaps ne sont pas perçus comme "Refus". Leur architecture colorimétrique est designée comme des "Actions" (orange).
3. **Cartes d'Explicativite** : Chaque poste suggere un affichage fluide de son pourquoi-matchant et la reedition CV ciblée.

---

## 8. ETAPE 7 : L'OBLIGATION D'UN SYSTEME AUTO-APPRENANT (TRACKING MLOPS)

C'est ici qu'intervient le pivot Big Data révolutionnaire de TalentFlow.
Les recommandations Qdrant, le sens, le scoring, le NLP : tout cela stagne si le système ne comprend pas qu'il est "dans l'erreur". Exemple: Si 500 informaticiens cliquent sur une offre "Développeur Python Junior", puis quittent instantanément l'offre parce qu'elle incluait le nom occulte d'une ville exilée qui a été cachée par l'algo, alors l'algo se trompe et la mathématique perd au contact du social.

### 8.1. Collecte Implicite (`UserInteractionCollector`)
Lorsque le candidat manipule le FrontEnd, un Token de Session le suit. L'algorithme ne pose pas la question "Es-tu satisfait ?" (Le taux de reponse sondage est < 1%). Il utilise l'implicatif :
1. L'application percoit les Card Swipes.
2. Elle calcule le temps de fixage écran (*Dwell Time*) : L'interface compte silencieusement les secondes au dela d'un seuil visible (le `read_seconds`).
3. L'action intentionnelle (*Postuler/Follow-up*) est un acte physique décisif (`CLICK`).

Le script Flutter interroge l'API Python (`track_user_interaction` asynchrone en arrière plan sous PostgreSQL).

### 8.2. Labelisation et Biais Cognitifs
La fonction locale `calculate_engagement_score()` distribue une évaluation absolue à posteriori.
- **Dwell Time Bref (Ex: Scroll/Fermeture)** : Label $0.0$. Le modele $MLRanking$ s'est fourvoyé. C'était un faux positif pour l'humain.
- **Etude Prolongee (Read\_seconds long)** : Label $0.6$. Offre pertinente mais friction à l'action.
- **Engagement Foudroyant (Clic intentionnel)** : Label $1.0$. Pertinence Maximum.

### 8.3. Entrainement Cyclique Automatisé par Orchestration Batch (DAG AIRFLOW)
Les bases de métadonnées massives sont useless si elles moisissent. TalentFlow clôt la boucle dans `airflow/dags/ml_retraining_dag.py`.
Plusieurs fois par semaine, à 3h du matin :
1. **La Phase de Collecte** : L'opérateur Airflow appelle PostgreSQL `collect_training_data`. Il collecte les 90 jours `days_back` d'anciennes recommandations.
2. **Transformation des Labels** : Il corrèle la "Feature Matrix $X$" primitive qui avait engendré la suggestion au "Label Réel Constaté $Y$".
3. **Réapprentissage Continu (Continuous Learning)** : Le service relance l'entrainement LightGBM sous Device GPU si applicable (`use_gpu: True`). Le LambdaRank recalcule intégralement le poids des noeuds, pour enfin comprendre par exemple, le désamour des postulants sur le feature Salarial face à la ville d'occupation. Le ML "s'ajuste" en continu aux humeurs culturelles des candidats.
4. **Validation Performance Assurée (Continuous Deployment)** : Avant de pousser ce nouveau "cerveau" `.pkl` à la production Backend API, l'opérateur lance un test NDCG validation Split (80/20). La condition critique (`PERFORMANCE_THRESHOLD = 0.65`) exige que la version V2 depasse mathématiquement 65% de précision. 
5. Si ce conditionnement est succès, l'artefact remplace le model courant. Les serveurs Redis Caches sont balayés de leur obsolete et TalentFlow entame son nouveau cycle de clarté pour l'aube. 

Ce système de boucle completement modulaire prouve à la fois  : 
- Qu'un processus RAG doit marier Vectorisation, NLP, Machine Learning d'Hyperpersonnalisation Rankée et MLOps Feedback Loop pour exister veritablement face à l'industrie du recrutement moderne.
