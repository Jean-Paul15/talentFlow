# TalentFlow Flutter (Android + Web)

Client candidat Flutter pour TalentFlow.

Le produit est centre sur la promesse:

`CV brut -> offres credibles -> strategie de candidature`

## Fonctionnalites principales

- auth utilisateur
- recherche d'offres via GraphQL
- copilote CV texte avec upload `PDF/DOCX/TXT`
- synthese finale `Gemini -> DeepSeek -> fallback deterministe`
- bloc `ATS-lite` structure
- historique serveur des recommandations
- favoris via GraphQL
- rapport PDF backend telechargeable depuis le Copilote et l'historique
- configuration runtime de l'URL API pour web, Android LAN et VPS

## Pre-requis

- Flutter SDK 3.35+
- Android Studio ou SDK Android
- Chrome pour le web

## Lancer en web local

```bash
cd frontend/talentflow_flutter
flutter run -d chrome --dart-define-from-file=env/web.local.json.example
```

## Lancer en Android LAN

Mettre l'IP reelle du PC dans `env/android.lan.json.example`, puis:

```bash
cd frontend/talentflow_flutter
flutter run -d android --dart-define-from-file=env/android.lan.json.example
```

## Variables de configuration

- `API_BASE_URL`
- `GRAPHQL_PATH`

La resolution est:
1. override runtime sauvegarde dans l'app
2. `--dart-define`
3. fallback par defaut

Voir `lib/core/app_config.dart`.

## Flux principal de demo

1. se connecter
2. importer ou coller un CV
3. lancer `Copilote CV`
4. lire la synthese finale, les scores ATS-lite et les offres credibles
5. telecharger le rapport PDF si l'analyse est sauvegardee
6. sauvegarder/ouvrir des favoris
7. revoir l'historique

## Notes

- en mobile, ne jamais utiliser `localhost`
- utiliser l'IP LAN du PC ou l'URL publique du VPS
- le frontend consomme `assistantStructured` en priorite; `assistantMessage` reste un fallback
- le rapport PDF est recupere via `GET /reports/history/:id.pdf` avec Bearer token
