# Architecture complète

## Décision d’architecture LLM
Le backend officiel utilise désormais:

- **Gemini** pour la génération user-facing
- **Mistral** pour l’enrichissement offline de `data-cleaning`
- **Qwen2.5:3b local** comme dernier secours optionnel pour `data-cleaning`
- **Qdrant** comme moteur vectoriel principal
- **MongoDB Silver** pour les données nettoyées
- **MinIO Bronze** pour le stockage brut

## Pourquoi ce choix
- éviter les doublons d’outils
- réduire les coûts d’exploitation
- simplifier le debugging
- rendre le comportement du système plus prévisible

## Conséquence
Il n’y a plus de dépendance officielle à un runtime LLM local pour démarrer la plateforme.
Le profil local reste optionnel et réservé aux postes de dev / self-hosted.
