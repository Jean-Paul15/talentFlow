# Fallback LLM

## Politique officielle
Le fallback depend du service:

- `recommendation`: **Gemini -> DeepSeek -> deterministe**
- `data-cleaning`: **Mistral -> deterministe**

## Recommendation: ordre exact
1. `GEMINI_API_KEY`
2. `GEMINI_API_KEY_FALLBACK`
3. `GEMINI_API_KEYS` restantes
4. `DEEPSEEK_API_KEY`
5. fallback deterministe metier

## DeepSeek scalable (cout + SLA)
- `deepseek-chat` par defaut
- `deepseek-reasoner` active uniquement sur cas complexes
- downgrade automatique vers `chat` quand:
  - budget journalier proche de la limite
  - ratio reasoner > `DEEPSEEK_REASONER_MAX_SHARE`
- file d'attente courte LLM:
  - `DEEPSEEK_QUEUE_MAX_SIZE`
  - `DEEPSEEK_QUEUE_WAIT_MS`
  - fallback deterministe si surcharge
- garde-fous RPM:
  - `DEEPSEEK_RPM_GLOBAL`
  - `DEEPSEEK_RPM_PER_IP`
- budget strict:
  - `DEEPSEEK_DAILY_TOKEN_BUDGET`
  - `DEEPSEEK_DAILY_COST_BUDGET_USD`

## Data-cleaning: ordre exact
1. `MISTRAL_API_KEY`
2. fallback `NER/patterns`

## Exemple

```env
LLM_PROVIDER=gemini
LLM_PROVIDER_ORDER=gemini,deepseek
GEMINI_API_KEY=...
GEMINI_API_KEY_FALLBACK=...
GEMINI_API_KEYS=
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_REASONER_MODEL=deepseek-reasoner
DEEPSEEK_MAX_OUTPUT_TOKENS_CHAT=700
DEEPSEEK_MAX_OUTPUT_TOKENS_REASONER=1600
DEEPSEEK_DAILY_TOKEN_BUDGET=500000
DEEPSEEK_DAILY_COST_BUDGET_USD=5.0
DEEPSEEK_REASONER_COMPLEXITY_THRESHOLD=1.0
DEEPSEEK_REASONER_MAX_SHARE=0.20
DEEPSEEK_QUEUE_CONCURRENCY=4
DEEPSEEK_QUEUE_MAX_SIZE=32
DEEPSEEK_QUEUE_WAIT_MS=900
DEEPSEEK_RPM_GLOBAL=120
DEEPSEEK_RPM_PER_IP=20
LLM_PROMPT_TEMPLATE_VERSION=v2
LLM_REPAIR_CACHE_TTL_SECONDS=300
DATA_CLEANING_LLM_PROVIDER=mistral
MISTRAL_API_KEY=...
```

## Si tout echoue
- `recommendation` reste sur une reponse deterministe
- `recommendation` tente DeepSeek avant le fallback deterministe
- `data-cleaning` renseigne `llm_degraded=true` puis continue via `NER/patterns`
