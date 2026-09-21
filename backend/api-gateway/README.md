# API Gateway

## Objectif
Ce service agit comme point d'entrée unique pour le frontend et orchestre les appels aux différents microservices.

## Fonctionnalités principales
- Gestion des requêtes GraphQL pour un accès flexible aux données.
- Authentification et autorisation des utilisateurs.
- Orchestration des appels aux microservices (ex. : FastAPI pour les calculs IA).

## Technologies
- Framework : NestJS
- GraphQL : Apollo Server
- Authentification : Passport.js (JWT)