# Architecture Backend - Fonctionnement global

## Vue synthetique
Le backend TalentFlow separe maintenant clairement les roles:

- **Gemini** pour la reponse finale visible par le candidat
- **DeepSeek** comme fallback provider final
- **Mistral** pour l'enrichissement offline du `data-cleaning`
- **NER + patterns** comme fallback garanti du `data-cleaning`
- **Qdrant local** comme moteur officiel de retrieval

```text
Sources -> Job Sourcing -> MinIO Bronze -> Data Cleaning -> MongoDB Silver
                                      -> Search Engine (Qdrant) -> Recommendation -> API Gateway -> Flutter
```

## Role des services
- `job-sourcing` collecte les offres via scraping et APIs
- `data-cleaning` normalise, enrichit et calcule qualite/fraicheur
- `search-engine` lit MongoDB Silver et maintient l'index Qdrant
- `recommendation` prend un CV texte, interroge Qdrant via `/search/by-vector` puis demande a Gemini de produire la synthese finale, avec DeepSeek en secours provider
- `api-gateway` expose un contrat GraphQL propre au frontend candidat et un endpoint PDF authentifie pour les rapports

## Politique LLM
- `recommendation`: **Gemini -> DeepSeek -> deterministe**
- `data-cleaning`: **Mistral principal**
- `fallback cleaning`: **NER + patterns**

Important:
- aucun LLM local n'est requis dans le runtime supporte
- `Qwen` n'est plus dans l'architecture officielle
- les rapports candidat sont generes cote backend via `GET /reports/history/:id.pdf`

## Politique produit
- le retrieval decide quelles offres sont credibles
- Gemini ne doit pas inventer d'offres
- si aucune offre n'est vraiment pertinente, la reponse finale est un **diagnostic no-match** avec actions conseillees

## Benefices
- meilleure separation online/offline
- moins de spaghetti multi-provider
- demo plus stable grace aux donnees deja nettoyees et indexees
- evolution plus simple du produit candidat sans toucher au pipeline Big Data
