# Recommendation ML System

## État actuel
Le service officiel de génération finale est branché sur **Gemini -> DeepSeek -> fallback deterministe**.
DeepSeek est piloté en mode scalable:
- `chat` par défaut
- `reasoner` auto pour cas complexes
- garde-fous RPM, queue, circuit-breaker et budget journalier

## Composants
- analyse CV texte
- recherche d’offres
- recommandations
- amélioration de CV
- cache et fallback déterministe

## Disponibilité
La haute disponibilité LLM repose sur plusieurs clés Gemini et un fallback provider DeepSeek, puis un mode déterministe si besoin.

## Statuts runtime
`llm_status` peut être:
- `used`
- `used_cached`
- `provider_error`
- `rate_limited_fallback`
- `queue_timeout_fallback`
- `fallback_used`

## Remarque
Les anciens chemins de code sont conservés uniquement pour compatibilité minimale et ne représentent plus l’architecture officielle.
