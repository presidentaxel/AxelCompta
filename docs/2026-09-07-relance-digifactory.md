# Relance Digifactory — retest du token, 07/09/2026

> Document à envoyer à Pierre BERTOLA. Fait suite au blocage signalé le
> 2026-09-01 (doc 16 §7) — toujours d'actualité un mois plus tard.

Bonjour Pierre,

On a retesté l'accès à l'API Digifactory ce jour (07/09/2026, 19:05 UTC)
avec le token qu'on a reçu. Toujours bloqué en 401, exactement comme
début septembre.

## Ce qu'on a testé

Trois appels, sur la base `https://entrepreneur.digifactory.fr/api/bridge` :

1. `GET /contacts` avec `Authorization: Bearer <token>`
2. `GET /contacts` avec `Authorization: <token>` (sans le préfixe `Bearer`,
   pour écarter une histoire de format d'en-tête)
3. `GET /categories` (une route différente, pour écarter un problème
   spécifique à `/contacts`)

## Résultat — identique sur les trois

```
HTTP/1.1 401 Unauthorized
{"error":{"exception":"UnauthorizedException","code":401,
 "reason":"An authentication is mandatory for this action","tag":"..."}}
```

Tags de trace (pour retrouver ces appels précis dans vos logs serveur,
07/09/2026 19:05:39 UTC) :
- `/contacts` avec Bearer : `6a9f0b031d415`
- `/contacts` sans Bearer : `6a9f0b034b1b0`
- `/categories` : `6a9f0b035c0d4`

## Ce qu'on a déjà écarté côté client

- Le token fait bien 64 caractères, aucun caractère parasite ni espace
  résiduel.
- Testé avec et sans le préfixe `Bearer`.
- TLS et routage fonctionnent : connexion HTTPS établie, bonne route
  atteinte, réponse JSON bien formée avec vos en-têtes CORS habituels
  (`Access-Control-Allow-Origin`, etc.). L'échec est bien au niveau de
  l'authentification côté serveur, pas un problème réseau ou de format de
  requête de notre côté.
- Le token utilisé se termine par `...8512`, pour confirmation rapide de
  votre côté que c'est bien celui que vous nous avez transmis.

## Questions pour débloquer

1. Le token est-il bien actif côté Digifactory (pas expiré, pas en attente
   d'activation) ?
2. Y a-t-il un filtrage par IP, ou un environnement (sandbox vs
   production) auquel nos appels devraient être adressés à la place ?
3. Le format d'en-tête attendu est-il bien `Authorization: Bearer <token>`
   comme documenté, ou autre chose ?

On reste dispo pour retester en direct avec vous si c'est plus rapide.

Merci,
Louis
