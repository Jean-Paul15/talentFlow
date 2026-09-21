# Integration LLM

## Politique officielle
Le backend TalentFlow separe maintenant les roles:

- `recommendation` = **Gemini -> DeepSeek -> fallback deterministe**
- `data-cleaning` = **Mistral principal**
- fallback `data-cleaning` = **NER + patterns**

## Recommendation / user-facing
Variables supportees:
- `GEMINI_API_KEY`
- `GEMINI_API_KEY_FALLBACK`
- `GEMINI_API_KEYS`
- `GEMINI_MODEL`
- `GEMINI_MODEL_PRIORITY`
- `GEMINI_TIMEOUT_SECONDS`
- `GEMINI_MAX_RETRIES`
- `GEMINI_RETRY_BASE_SECONDS`
- `DEEPSEEK_ENABLED`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_TIMEOUT_SECONDS`
- `DEEPSEEK_MAX_RETRIES`
- `DEEPSEEK_RETRY_BASE_SECONDS`

Le chemin user-facing utilise le SDK officiel `google-genai`.

Important:
- plusieurs cles Gemini d'un meme projet n'augmentent pas le quota
- elles servent a la haute disponibilite et a la bascule entre projets
- DeepSeek reste un fallback provider final, pas la voix principale

## Data-cleaning
Variables supportees:
- `DATA_CLEANING_LLM_PROVIDER=mistral`
- `MISTRAL_API_KEY`
- `MISTRAL_MODEL`
- `MISTRAL_TIMEOUT_SECONDS`
- `MISTRAL_MAX_RETRIES`
- `MISTRAL_RETRY_BASE_SECONDS`

Ordre d'execution:
1. Mistral cloud
2. NER / patterns

## Motivation
- eviter le spaghetti multi-provider
- garder une voix utilisateur unique
- decharger le batch offline hors de Gemini
- conserver un mode degrade deterministe
