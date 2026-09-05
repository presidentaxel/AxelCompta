# backend/ — axelcompta

Monolithe modulaire Python (FastAPI / SQLAlchemy / Postgres), découpage complet
défini en [doc 03 §3](../docs/03-architecture.md#3--découpage-en-modules-monolithe-modulaire).

> **Statut au 2026-09-05 : squelette d'interfaces, aucune logique métier.**
> Louis a donné le top départ pour cette étape (doc 12 §0.1 reste sinon la
> référence — relecture associé encore en attente). Chaque module a des
> signatures (classes, dataclasses, ABC) qui s'importent et passent mypy
> strict/ruff/import-linter, mais aucune méthode n'est implémentée : rien ne
> tourne encore (pas de DB, pas d'appel réseau, pas de calcul).

## Reproduire les vérifications

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                # importe tous les modules
.venv/bin/mypy axelcompta          # strict, doit rester à 0 issue
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/lint-imports              # frontières de dépendance (doc 03 §3)
```

Les quatre passent à 0 erreur sur ce squelette (dernière vérification :
2026-09-05).

## Deux niveaux de lecture dans cet arbre

Ce découpage est celui du **produit final V1** (doc 03/12), pas seulement de
la démo. Chaque README de module précise donc deux statuts distincts :

- **Démo (doc 17)** : ce que ce module doit faire pour la démo interne d'un
  mois, scope volontairement réduit (voir [doc 17 §3](../docs/17-plan-demo-backend.md#3-coupes-de-scope-assumées)).
- **V1 cible (doc 12)** : ce que ce module doit faire pour le produit réel,
  à capacité normale (1-2 devs, phases pluri-mensuelles).

Un module marqué « non prévu pour la démo » existe déjà dans l'arbre (dossier
+ README) mais reste vide de code tant que sa phase n'est pas atteinte —
l'idée est de ne jamais avoir à ré-organiser l'arbre plus tard, seulement à
le remplir.

Détail complet de la correspondance arbre ↔ docs : [docs/18-organisation-code.md](../docs/18-organisation-code.md).

## Règles de dépendance (vérifiées par import-linter en CI, doc 03 §3)

- `ledger` ne dépend de rien sauf `core`. Jamais de `categorize`, `ml`, `api`.
- `categorize` produit des `ProposedEntry` ; seul `workflow` peut les
  transformer en écritures via `ledger`, après validation.
- `api` n'importe que les façades publiques de chaque module (`module/service.py`).
- Personne n'importe `ml` au runtime : les modèles sont chargés comme artefacts.

## Modules

| Module | Rôle en une ligne | Démo (doc 17) | V1 (doc 12) |
|---|---|---|---|
| [`core/`](axelcompta/core/README.md) | Types partagés : monnaie, erreurs, ids typés | Actif (minimal) | Actif |
| [`tenants/`](axelcompta/tenants/README.md) | Tenants, dossiers, statuts/régimes | Réduit (1 dossier en dur) | Actif |
| [`packs/`](axelcompta/packs/README.md) | Packs métier : taxonomies, règles, templates | Actif (pack VTC réduit) | Actif |
| [`ingestion/providers/`](axelcompta/ingestion/providers/README.md) | Interface `DataProvider` + implémentations | Actif | Actif |
| [`documents/`](axelcompta/documents/README.md) | Justificatifs, OCR, Factur-X, matching | Non prévu | Actif |
| [`categorize/`](axelcompta/categorize/README.md) | Pipeline règles → ML → LLM → revue humaine | Réduit (règles + ML, pas de LLM) | Actif |
| [`anomaly/`](axelcompta/anomaly/README.md) | Détection d'abus / anomalies | Non prévu | Actif |
| [`ledger/`](axelcompta/ledger/README.md) | ❤️ Moteur comptable pur | Actif | Actif |
| [`closing/`](axelcompta/closing/README.md) | Clôture d'exercice, états financiers | Réduit | Actif |
| [`filings/`](axelcompta/filings/README.md) | Renderers FEC, PDF, EDI-TDFC, INPI | Réduit (PDF simplifié seulement) | Actif |
| [`workflow/`](axelcompta/workflow/README.md) | Validation, revue, signature électronique | Non prévu | Actif |
| [`api/`](axelcompta/api/README.md) | Routes FastAPI, auth, permissions | Réduit (pas d'auth) | Actif |
| [`ml/`](axelcompta/ml/README.md) | Entraînement, évaluation, registry modèles | Non prévu (modèle déjà entraîné réutilisé) | Actif |

## Ce qui existe déjà et sera réutilisé (hors de cet arbre)

Le travail d'audit dans [`_AUDIT_DONNEES/`](../_AUDIT_DONNEES/README.md) n'est
pas dupliqué ici : `packs/` et `categorize/` s'y réfèrent directement (pack
VTC, modèle TF-IDF entraîné, CSV FEC labellisé). Voir [doc 17 §4bis](../docs/17-plan-demo-backend.md#4bis-ce-quon-réutilise-déjà-accélérateurs-issus-de-laudit).
