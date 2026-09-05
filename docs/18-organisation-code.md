# 18 — Organisation du code

> Statut : arborescence et documentation créées, **aucun code produit** —
> conforme au garde-fou du [README](../README.md) et du [doc 12 §0.1](12-roadmap-todo.md)
> (relecture doc + top départ de Louis encore à venir). Dernière mise à jour : 2026-09-05.

Ce doc fait le lien entre l'arborescence réelle du repo (`backend/`,
`frontend/`) et le découpage en modules défini en [doc 03 §3](03-architecture.md#3--découpage-en-modules-monolithe-modulaire).
Chaque dossier de `backend/axelcompta/*/` a son propre `README.md` avec le
même triptyque : **rôle**, **statut démo (doc 17)** vs **statut V1 (doc 12)**,
**doc de référence**.

## Pourquoi l'arbre complet dès maintenant, alors que seule la démo est visée à court terme

Le module `ledger/` (par exemple) doit être écrit une fois, bien, avec les
bonnes frontières de dépendance — pas retravaillé quand on passera de la
démo à la V1. L'arbre ci-dessous est donc celui **du produit final** ; ce
qui change entre démo et V1, c'est le contenu de chaque dossier, jamais sa
position ni ses règles de dépendance.

## Vue d'ensemble

```text
AxeLCompta/
├── backend/axelcompta/
│   ├── core/                 # actif démo — Money, ids, erreurs
│   ├── tenants/               # réduit démo — 1 dossier en dur (V1 : multi-tenant + matrice statut)
│   ├── packs/                 # actif démo — pack VTC réduit (V1 : taxonomie complète)
│   ├── ingestion/
│   │   └── providers/         # actif démo — DataProvider + chemins A/B/C
│   ├── documents/             # non prévu démo (OCR, justificatifs — V1 seulement)
│   ├── categorize/            # réduit démo — règles + ML, pas de LLM ni revue humaine
│   ├── anomaly/                # non prévu démo (V1 seulement)
│   ├── ledger/                # ❤️ actif démo — moteur pur, golden test doc 17 §7
│   ├── closing/                # réduit démo — clôture minimale
│   ├── filings/                # réduit démo — PDF simplifié (V1 : FEC/EDI/INPI)
│   ├── workflow/                # non prévu démo (revue humaine, signature — V1 seulement)
│   ├── api/                    # réduit démo — pas d'auth (V1 : auth/MFA/permissions)
│   └── ml/                      # non prévu démo — modèle déjà entraîné réutilisé tel quel
├── frontend/                   # réduit démo — rapport HTML/notebook (V1 : Next.js complet)
└── _AUDIT_DONNEES/              # existant, inchangé — source de données pour packs/ et categorize/
```

## Graphe de dépendances (règle vérifiée par import-linter en CI, doc 03 §3)

```mermaid
graph TD
    core["core"]
    tenants["tenants"] --> core
    packs["packs"] --> core
    documents["documents"] --> core
    documents --> tenants
    ingestion["ingestion/providers"] --> core
    ingestion --> tenants
    categorize["categorize"] --> core
    categorize --> packs
    categorize --> ingestion
    categorize --> documents
    anomaly["anomaly"] --> core
    anomaly --> categorize
    ledger["ledger ❤️"] --> core
    closing["closing"] --> core
    closing --> ledger
    filings["filings"] --> core
    filings --> closing
    workflow["workflow"] --> core
    workflow --> categorize
    workflow --> ledger
    ml["ml"] -. artefact chargé, jamais importé .-> categorize
    api["api"] -. façades publiques seulement .-> tenants
    api -. façades publiques seulement .-> categorize
    api -. façades publiques seulement .-> ledger
    api -. façades publiques seulement .-> closing
    api -. façades publiques seulement .-> filings
    api -. façades publiques seulement .-> workflow
```

**Ce que ce graphe interdit, explicitement (doc 03 §3) :**
- `ledger` → `categorize`, `ml`, ou `api` : jamais, dans aucun sens.
- `categorize` → `ledger` directement : passe obligatoirement par `workflow`.
- Tout import direct de `ml` au runtime : les modèles sont des artefacts chargés.

## Ce qui se passe en pratique pour la démo (doc 17)

La coupe verticale de la démo (« faire tourner tout le pipeline bout-en-bout
dès les premiers jours », doc 17 §2) traverse tous les modules « actif » ou
« réduit » du tableau ci-dessus. **Semaine 0 (faite) saute `categorize`** —
il n'entre en jeu qu'en semaine 2, une fois les vrais templates de
ventilation TVA nécessaires :

```
ingestion/providers  →  ingestion/reconciliation  →  ledger  →  closing  →  filings
  (fixtures, golden      (bouchon : égalité de       (512/706    (bouchon :   (PDF
   test doc 17 §7)        montant, doc 13 §4.2         bruts,      solde par    bouchon,
                           pour la vraie version)       doc 17 §7)  compte)      reportlab)
```

Semaine 2 (à faire) insère `categorize` (règles + ML) entre la réconciliation
et `ledger`, pour produire les `ProposedEntry` qui pilotent les vrais
templates d'écriture (doc 13 §5.3, ventilation TVA complète). `tenants`,
`packs`, `core` et `api` restent transverses.

`backend/axelcompta/demo.py` est la composition root qui câble tout ça —
absent du découpage doc 03 §3 exprès : c'est un point d'entrée (comme `api/`),
pas un module d'architecture, donc pas soumis aux mêmes contraintes de
dépendance.

## Statut d'implémentation actuel

**Semaines 0 et 1 du doc 17 faites (2026-09-05)** :
- Semaine 0 : `python -m axelcompta.demo` produit un vrai PDF à partir des
  fixtures du golden test (doc 17 §7), en mémoire (`InMemoryLedgerService`,
  pas de DB requise). Postgres + Alembic sont montés (`docker-compose.yml`,
  `migrations/`) et vérifiés contre un vrai conteneur
  (`PostgresLedgerService`, tests d'intégration) mais pas encore branchés
  dans `demo.py`.
- Semaine 1 : les 5 providers rendent des données (plus aucun
  `NotImplementedError`). `FileImportProvider` (chemin C) rejoue le vrai CSV
  audit (36 152 lignes, regroupement des composites, inversion du signe
  FEC → relevé bancaire) — testé contre le fichier réel, pas seulement des
  fixtures. `DigifactoryProvider`/`RolleeProvider` restent chemin B
  (fixtures) : token 401 et sandbox non vérifié toujours d'actualité côté
  Louis, chemin A non tenté.

Détail et commandes : [backend/README.md](../backend/README.md).

Prochaine étape : semaine 2 du doc 17 (`categorize` — règles + ML existant —
inséré entre réconciliation et `ledger`, vraie ventilation TVA doc 13 §5.3,
algorithme de réconciliation réel doc 13 §4.2).
