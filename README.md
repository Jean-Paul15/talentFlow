<div align="center">
  <h1>TalentFlow</h1>
  <p><b>Un pipeline big data qui transforme des offres d'emploi éparpillées sur le web en une recherche sémantique et en analyses CV / offre, servies à une application Flutter.</b></p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/NestJS-E0234E?style=for-the-badge&logo=nestjs&logoColor=white" alt="NestJS"/>
  <img src="https://img.shields.io/badge/Apache%20Spark-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white" alt="Apache Spark"/>
  <img src="https://img.shields.io/badge/Apache%20Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white" alt="Apache Kafka"/>
  <img src="https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <br/><br/>
  <img src="https://img.shields.io/badge/Licence-Tous%20droits%20r%C3%A9serv%C3%A9s-lightgrey?style=flat-square" alt="Licence : tous droits réservés"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/Dart-0175C2?style=flat-square&logo=dart&logoColor=white" alt="Dart"/>
  <p>
    <a href="#démarrer-en-cinq-minutes">Démarrer</a> ·
    <a href="#comment-ça-marche">Architecture</a> ·
    <a href="#stack-technique">Stack</a> ·
    <a href="#structure-du-dépôt">Structure</a> ·
    <a href="#tests">Tests</a>
  </p>
</div>

## Sommaire

- [Ce que ça apporte](#ce-que-ça-apporte)
- [Le problème](#le-problème)
- [Démarrer en cinq minutes](#démarrer-en-cinq-minutes)
- [Comment ça marche](#comment-ça-marche)
- [Stack technique](#stack-technique)
- [Structure du dépôt](#structure-du-dépôt)
- [Tests](#tests)
- [Limites et suite](#limites-et-suite)
- [Licence et contact](#licence-et-contact)

## Ce que ça apporte

- **Un flux de bout en bout, de la page web à l'écran du candidat.** Collecte (Scrapy, Adzuna, JSearch), Kafka, Spark Structured Streaming, lac MinIO, MongoDB, Qdrant, puis passerelle NestJS et client Flutter. Chaque étape est un service isolé.
- **Des données traitées pour être utilisables, pas seulement stockées.** Déduplication par empreinte dans Redis dès la collecte, couches Bronze et Silver, calcul de fraîcheur avec durée de validité par offre, pénalités pour les contenus bruités des job boards.
- **Des appels LLM qui ne bloquent pas le service.** Les analyses de CV passent par Gemini ou DeepSeek, avec cache, budget et disjoncteur par fournisseur (5 échecs ouvrent le circuit, 60 secondes avant nouvel essai par défaut, réglable par variables d'environnement).

## Le problème

Un candidat cherche « data engineer » et tombe sur la même annonce publiée sous trois titres, sur quatre sites, dont une périmée depuis des semaines. Chaque site structure ses pages à sa façon. Comparer son CV à ces offres se fait à la main.

TalentFlow règle cela en amont. Il collecte en continu, normalise dans un lac de données, retire les doublons et les offres expirées, puis indexe le texte par sens plutôt que par mots-clés. Le CV est ensuite comparé aux offres : écarts de compétences, score de matching.

## Démarrer en cinq minutes

Prérequis : Docker et Docker Compose.

```bash
cd backend
cp .env.example .env
# renseigner les valeurs CHANGEME dans .env (mots de passe, JWT_SECRET, clés LLM)
docker compose --profile lake-only up -d --build
docker compose ps
```

Ce profil démarre l'infrastructure de base, MinIO, `lake-api` (port 8004) et le tableau de bord Streamlit (port 8501). Pour ajouter la passerelle, la recommandation et la recherche, utilisez `--profile api`. Les scripts `scripts/bash/env-generator.sh` et `scripts/powershell/env-generator.ps1` génèrent les secrets. La passerelle refuse de démarrer sans `JWT_SECRET`.

## Comment ça marche

```mermaid
flowchart LR
  S[Sites et API d'emploi] --> JS[job-sourcing]
  JS -->|empreinte| R[(Redis)]
  JS --> K[(Kafka)]
  K --> SS[spark-streaming]
  SS --> B[(MinIO Bronze)]
  B --> DC[data-cleaning]
  DC --> M[(MongoDB Silver)]
  M --> SE[search-engine]
  SE --> Q[(Qdrant)]
  B --> LA[lake-api]
  SE --> RC[recommendation]
  RC -->|LLM avec cache et disjoncteur| L[Gemini / DeepSeek]
  RC --> GW[api-gateway]
  SE --> GW
  GW --> PG[(PostgreSQL)]
  GW --> FL[Client Flutter]
  AF[Airflow] -.-> JS
  AF -.-> DC
  PR[Prometheus / Grafana] -.-> GW
```

Trois choix structurent le projet.

**Un lac en deux couches.** Bronze garde la donnée brute telle que Spark l'a reçue de Kafka, avec partition et offset. Silver contient la donnée nettoyée dans MongoDB. `data-cleaning` lit Bronze dans MinIO : une règle de nettoyage modifiée s'applique à la donnée déjà collectée, sans nouvelle collecte.

**Dédupliquer à la source.** `job-sourcing` calcule une empreinte par offre et l'interroge dans Redis avant de publier sur Kafka. Les doublons n'entrent pas dans le pipeline, ce qui épargne Spark, le stockage et l'index.

**La fraîcheur comme règle de classement.** `data-cleaning` annote chaque offre (date, source de la date, durée de validité). `search-engine` filtre les offres expirées et rétrograde les anciennes. Les tests couvrent le cas d'une offre internationale de 38 jours jugée périmée avec un seuil de 21 jours.

Le scraping, lui, apprend : le module `smart_parser` mémorise par domaine les sélecteurs CSS qui ont fonctionné et réutilise les meilleurs sur les pages suivantes.

## Stack technique

| Domaine | Technologies | Rôle dans le projet |
|---|---|---|
| Passerelle | <img src="https://img.shields.io/badge/NestJS-E0234E?style=flat-square&logo=nestjs&logoColor=white" alt="NestJS"/> <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/> <img src="https://img.shields.io/badge/Prisma-2D3748?style=flat-square&logo=prisma&logoColor=white" alt="Prisma"/> <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/> <img src="https://img.shields.io/badge/GraphQL-E10098?style=flat-square&logo=graphql&logoColor=white" alt="GraphQL"/> <img src="https://img.shields.io/badge/Passport%20JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" alt="Passport JWT"/> | Authentification, API GraphQL, historique et rapports PDF (pdf-lib) pour le client (NestJS 10) |
| Services de données | <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/> <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/> <img src="https://img.shields.io/badge/Scrapy-60A839?style=flat-square&logo=scrapy&logoColor=white" alt="Scrapy"/> <img src="https://img.shields.io/badge/PySpark-E25A1C?style=flat-square&logo=apachespark&logoColor=white" alt="PySpark"/> | Collecte, nettoyage, API de lecture du lac, streaming Kafka vers MinIO (PySpark 3.5) |
| Stockage et messagerie | <img src="https://img.shields.io/badge/Apache%20Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white" alt="Apache Kafka"/> <img src="https://img.shields.io/badge/MinIO-C72E49?style=flat-square&logo=minio&logoColor=white" alt="MinIO"/> <img src="https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB"/> <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis"/> <img src="https://img.shields.io/badge/Qdrant-DC244C?style=flat-square&logo=qdrant&logoColor=white" alt="Qdrant"/> <img src="https://img.shields.io/badge/Elasticsearch-005571?style=flat-square&logo=elasticsearch&logoColor=white" alt="Elasticsearch"/> | Transport des offres, lac Bronze, couche Silver, empreintes de déduplication, index vectoriel et index texte |
| IA | <img src="https://img.shields.io/badge/fastembed-555555?style=flat-square" alt="fastembed"/> <img src="https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Gemini"/> <img src="https://img.shields.io/badge/DeepSeek-4D6BFE?style=flat-square&logo=deepseek&logoColor=white" alt="DeepSeek"/> <img src="https://img.shields.io/badge/pytesseract-555555?style=flat-square" alt="pytesseract"/> | Embeddings multilingues (paraphrase-multilingual-MiniLM-L12-v2), analyse de CV par LLM, OCR |
| Orchestration et supervision | <img src="https://img.shields.io/badge/Airflow-017CEE?style=flat-square&logo=apacheairflow&logoColor=white" alt="Airflow"/> <img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white" alt="Prometheus"/> <img src="https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white" alt="Grafana"/> <img src="https://img.shields.io/badge/cAdvisor-555555?style=flat-square" alt="cAdvisor"/> <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit"/> | DAGs de collecte et de nettoyage, métriques, tableaux de bord, interface de suivi du lac |
| Client | <img src="https://img.shields.io/badge/Flutter-02569B?style=flat-square&logo=flutter&logoColor=white" alt="Flutter"/> <img src="https://img.shields.io/badge/Dart-0175C2?style=flat-square&logo=dart&logoColor=white" alt="Dart"/> | Application candidat (Dart 3.9 ou plus) |
| Déploiement | <img src="https://img.shields.io/badge/Docker%20Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Compose"/> <img src="https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white" alt="Kubernetes"/> <img src="https://img.shields.io/badge/GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions"/> <img src="https://img.shields.io/badge/Nginx-009639?style=flat-square&logo=nginx&logoColor=white" alt="Nginx"/> | Profils Compose, manifestes Kubernetes, workflows de déploiement et de tests de fumée, proxy |

## Structure du dépôt

```
backend/
  api-gateway/       NestJS (auth, GraphQL, historique, rapports PDF)
  job-sourcing/      Scrapy, clients d'API, producteur Kafka
  spark-streaming/   Kafka vers MinIO Bronze
  data-cleaning/     Bronze vers Silver (MongoDB)
  lake-api/          API de lecture du lac
  search-engine/     Embeddings et recherche Qdrant
  recommendation/    Analyse CV/offre, LLM, classifieur de CV
  dashboard/         Tableau de bord Streamlit
  monitoring/        Prometheus, Grafana, règles d'alerte
  orchestration/     DAGs Airflow, manifestes Kubernetes
  shared/            Modules Python communs
  config/, nginx/, scripts/
  docker-compose.yml
docs/                Notes d'architecture
frontend/talentflow_flutter/   Client Flutter
.github/workflows/   Déploiement et tests de fumée
```

## Tests

Pour vérifier le code, commencez par les tests :

```bash
cd backend/data-cleaning && python -m pytest tests
cd backend/search-engine && python -m pytest tests
```

Ils sont exécutables sans les services. Les tests de `recommendation`, le test de fumée de la passerelle (`npm run test:e2e:smoke`) et `flutter test` demandent leurs dépendances ou une passerelle active.

## Limites et suite

Le projet vise une démonstration d'architecture, pas un service en production. Ce périmètre est un choix.

- **Données.** Seuls de petits échantillons synthétiques sont fournis. Les données réelles viennent de la collecte et ne sont pas redistribuées.
- **Ressources.** La pile complète (Kafka, Spark, Elasticsearch, Qdrant, Airflow) est lourde. Les profils Compose permettent de n'en lancer qu'une partie.
- **LLM.** Les analyses de CV demandent des clés d'API externes.
- **Tests.** Les services de données sont testés. La passerelle n'a qu'un test de fumée et le client Flutter un seul test de widget. Étendre cette couverture est la suite la plus utile.
- **Déploiement.** Les workflows GitHub Actions supposent un hôte distant configuré par secrets (`OCI_HOST`, `OCI_USER`, `OCI_SSH_KEY`). Les noms de domaine sont remplacés par `example.com`.
- **Documentation.** Certaines notes de `docs/` datent du développement et peuvent différer du code. En cas d'écart, le code fait foi.

Le client Flutter se lance avec `flutter run -d chrome --dart-define-from-file=env/web.local.json.example` depuis `frontend/talentflow_flutter`.

## Licence et contact

Licence : tous droits réservés. La lecture du code à des fins d'évaluation est permise. Voir le fichier `LICENSE`.

Jean-Paul ADOGLI, étudiant ingénieur en data science et big data. GitHub : [Jean-Paul15](https://github.com/Jean-Paul15).
