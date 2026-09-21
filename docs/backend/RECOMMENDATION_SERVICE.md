# Recommendation Service

## Mode officiel
Le service de recommandation fonctionne en **Gemini -> DeepSeek -> fallback deterministe**.

Ordre d'execution:
1. tentative avec `GEMINI_API_KEY`
2. tentative avec `GEMINI_API_KEY_FALLBACK`
3. tentative avec la suite eventuelle de `GEMINI_API_KEYS`
4. tentative avec `DEEPSEEK_API_KEY`
5. si toutes echouent: reponse deterministe applicative

Important:
- plusieurs cles d'un meme projet Google n'augmentent pas le quota
- elles servent a la rotation et a la haute disponibilite
- DeepSeek est un fallback final de securite, pas un remplacement de Gemini
- DeepSeek active `chat` par defaut et `reasoner` seulement sur cas complexes

## Scalabilite / cout
- cache LLM en Redis (resultat + reparation courte)
- file d'attente LLM courte (concurrency + timeout)
- garde-fous RPM DeepSeek (global + par IP)
- budget strict journalier tokens + cout USD
- circuit-breaker provider pour limiter les cascades d'erreur

Statuts `llm_status` principaux:
- `used`
- `used_cached`
- `provider_error`
- `rate_limited_fallback`
- `queue_timeout_fallback`
- `fallback_used`
- `no_match`

## Ce que le service ne fait pas
- pas de fallback Mistral
- pas de fallback Qwen local
- pas de dependance a un conteneur LLM local

## Chemin stable
- `backend/recommendation/main.py`
- `backend/recommendation/api/routes_cv_text_async.py`
