# Verification runtime

## Ce qui est attendu
- `LLM_PROVIDER=gemini`
- `LLM_PROVIDER_ORDER=gemini,deepseek`
- `GEMINI_API_KEY` configuree
- `DEEPSEEK_ENABLED=true`
- `DEEPSEEK_API_KEY` configuree si le fallback provider est utilise
- `DATA_CLEANING_LLM_PROVIDER=mistral`
- `MISTRAL_API_KEY` configuree si `DATA_CLEANING_LLM_ENABLED=true`

## Verifications minimales
1. `docker compose config` standard ne doit exposer aucun service LLM local
2. `recommendation` doit demarrer sans dependance locale LLM
3. `data-cleaning` doit continuer si Mistral est indisponible
4. le mode degrade doit rester deterministe

## Verification grep

```bash
rg -n "GEMINI_API_KEY|MISTRAL_API_KEY" backend
```

Resultat attendu: uniquement les chemins prevus (`recommendation`, `data-cleaning`, compose, docs).
