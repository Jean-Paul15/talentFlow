# LangChain / GraphQL Integration

## État actuel
L’intégration historique basée sur plusieurs providers n’est plus l’architecture officielle.

## Politique retenue
- Gemini only pour les réponses LLM
- Mistral pour le nettoyage offline
- Qwen local uniquement en secours de `data-cleaning`
- fallback Gemini par seconde clé
- si tout échoue: réponse ou enrichissement déterministe

## Note
Les anciens schémas d’intégration multi-provider ne sont plus la référence de production.
