# ADR-003 — Hébergement et base de données

**Date :** 2026-06-16 — Mise à jour : 2026-06-16
**Statut :** partiellement accepté — base de données tranchée, compute à décider quand le code est stable
**Décideurs :** Louis Vedovato

## Contexte

AxeLCompta traite des données bancaires et fiscales de personnes morales françaises. Le client pilote est dans le secteur parabancaire (gestionnaire de chauffeurs VTC). Ce type de client soumet généralement un questionnaire sécurité fournisseur avec des exigences sur la localisation des données et la souveraineté.

---

## Décision 1 — Base de données : Supabase ✅ (retenu)

**Supabase est le choix retenu pour la base de données** (dev, staging et prod jusqu'à preuve du contraire).

Supabase = PostgreSQL managé avec tooling (dashboard SQL, RLS visuel, backups, PITR). Tout ce qui est prévu dans l'architecture (SQLAlchemy, Alembic, RLS multi-tenant) fonctionne sans modification — c'est une connection string PostgreSQL standard.

| Critère | Supabase | Scaleway Managed PG |
|---------|----------|-------------------|
| Prix | **$25/mois** (Pro) | ~€50/mois |
| PITR | ✅ 7 jours inclus | ✅ inclus |
| RLS | ✅ first-class | Manuel |
| Dashboard SQL | ✅ excellent | pgAdmin manuel |
| Société | 🇺🇸 US (données Frankfurt 🇩🇪) | 🇫🇷 France |
| CLOUD Act | ⚠️ applicable | ✅ non applicable |

### Risque CLOUD Act

Supabase est une société américaine. Le CLOUD Act permet aux autorités US d'accéder aux données d'une société US même hébergées en EU. Ce risque est **accepté provisoirement** avec un déclencheur clair pour le réexaminer.

### Plan de migration si nécessaire

La migration de Supabase vers n'importe quel PostgreSQL managé (Scaleway, OVHcloud) se résume à :

1. `pg_dump` depuis Supabase → `pg_restore` sur la cible
2. Changer `DATABASE_URL` dans les variables d'environnement
3. Rejouer `alembic upgrade head` sur la cible pour vérifier la cohérence
4. Basculer le DNS / la config applicative

**Durée estimée : ½ journée.** Ce n'est pas une refonte — à condition de ne jamais utiliser de fonctionnalités propriétaires Supabase (PostgREST auto-généré, Supabase Auth, Supabase Storage). Règle : **n'utiliser que la connection string PostgreSQL standard**. Tout passe par SQLAlchemy et Alembic.

### Déclencheur de réexamen

Migrer vers Scaleway ou OVHcloud Managed PostgreSQL si **le questionnaire sécurité d'un client exclut explicitement les prestataires soumis au CLOUD Act.** Pas avant.

---

## Décision 2 — Compute / infra applicative : à trancher plus tard

La décision sur le compute (VMs, containers, PaaS) est reportée à quand le code est suffisamment avancé pour connaître les contraintes réelles (taille des images Docker, besoins mémoire pour les modèles ML, fréquence des jobs).

### Options retenues pour évaluation

| Option | Avantage principal | Inconvénient |
|--------|-------------------|-------------|
| **Scaleway** (Containers ou Instances) | Société française, bon équilibre DX/contrôle | Plus d'ops que PaaS |
| **OVHcloud** (Public Cloud) | Argument fort face aux banques, SecNumCloud possible | DX plus rugueuse |
| **Clever Cloud** | Zéro ops, PaaS français | Moins adapté aux workers ML longue durée |

### Déclencheur de décision

Trancher quand : premier déploiement staging réel avec données synthétiques (Phase 1, tâche 1.1). La contrainte de localisation France reste non négociable pour la production.

---

## Règle transverse : aucun lock-in propriétaire

Quelle que soit la décision finale sur le compute :
- **Base de données** : SQLAlchemy + Alembic uniquement, jamais le client JS Supabase ou PostgREST
- **Stockage fichiers** : SDK S3 standard (`boto3`), jamais le SDK Supabase Storage
- **Auth** : implémentation maison (FastAPI + JWT), jamais Supabase Auth

Ces trois règles garantissent que changer de provider = changer des variables d'environnement, pas réécrire du code.

**Exception assumée pour la démo (doc 17, décidée 2026-09-07)** : les
comptes gestionnaire/chauffeur de la démo utilisent **Supabase Auth**
(rapidité de mise en œuvre, premier vrai système de comptes du projet).
C'est une entorse consciente à la règle ci-dessus, pas un changement de
décision — **la V1 doit repasser sur l'implémentation maison** avant le
pilote, sous peine du lock-in que cette règle existe pour éviter. Ne pas
laisser Supabase Auth s'installer par défaut faute d'y revenir.
