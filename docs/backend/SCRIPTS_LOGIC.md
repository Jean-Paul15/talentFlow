# Logique des scripts

## Generateurs `.env`
Les scripts de configuration doivent produire deux blocs distincts:

1. `recommendation = Gemini`
2. `data-cleaning = Mistral`
3. `local-llm = Qwen optionnel, desactive par defaut`

## Troubleshooting
Les scripts de diagnostic doivent verifier:

1. `LLM_PROVIDER=gemini`
2. presence de la cle Gemini principale
3. presence de `MISTRAL_API_KEY` si `DATA_CLEANING_LLM_ENABLED=true`
4. coherence entre `Gemini` (recommendation) et `Mistral` (data-cleaning)

Ils ne doivent tester `localhost:11434` que si le profil `local-llm` est explicitement active.

## Auto-orchestrateur
Le runtime officiel ne depend d'aucun LLM local.
Le profil `local-llm` reste reserve aux postes de dev / self-hosted.
