# ADR-001 — Monolithe modulaire plutôt que microservices

**Date :** 2026-06-16
**Statut :** accepté
**Décideurs :** Louis Vedovato

## Contexte

AxeLCompta est développé par une équipe de 1 à 2 développeurs. Le système couvre ingestion bancaire, catégorisation ML/LLM, moteur comptable, clôture et télédéclaration. Ces domaines sont distincts mais fortement couplés par les données (une transaction traverse tous les modules).

## Décision

**Architecture monolithe modulaire.** Un seul processus backend déployé, organisé en modules internes aux frontières strictes (imports vérifiés par `import-linter` en CI). Pas de microservices, pas de services séparés hors Postgres et stockage objet.

## Alternatives considérées

**Microservices :** chaque module (ingestion, ledger, ML…) est un service indépendant avec sa propre base de données et son API.
- Rejeté : surcharge opérationnelle prohibitive à 2 devs (déploiements, monitoring distribué, réseau, versioning des contrats inter-services). La complexité accidentelle dépasserait la complexité essentielle du projet.

**Microservices partiels (ledger isolé) :** seul le cœur comptable est un service séparé pour garantir son indépendance.
- Rejeté : l'indépendance de `ledger/` est garantie par les règles de dépendance (vérifiées en CI), pas par la séparation de déploiement. Coût sans bénéfice à ce stade.

## Conséquences

- **Avantages :** déploiement simple (une image Docker), debugging sans traces distribuées, transactions ACID entre modules, refactoring interne possible sans contrats d'API inter-services.
- **Inconvénients :** scaling horizontal limité à la réplication de l'instance entière (acceptable pour 200 dossiers en V1 ; à reconsidérer si volume × 100).
- **Règle à maintenir :** les frontières de module (doc 03 §3) doivent être aussi strictes que des frontières de service — `import-linter` bloquant en CI est la garantie.
- **Porte de sortie :** si un module doit être extrait en service séparé (ex. `ml/` pour le scaling GPU), il est déjà isolé derrière une interface — l'extraction est chirurgicale, pas une refonte.
