# backend/ — axelcompta

Monolithe modulaire Python (FastAPI / SQLAlchemy / Postgres), découpage complet
défini en [doc 03 §3](../docs/03-architecture.md#3--découpage-en-modules-monolithe-modulaire).

> **Statut au 2026-09-05 : doc 17 semaines 0 à 3 faites.** Une commande
> unique produit un PDF **qui ressemble enfin à un compte de résultat + un
> bilan** (doc 17 §2 : « coupe verticale d'abord », semaine par semaine on
> remplace les bouchons par du réel). Ventilation TVA réelle (golden test
> Uber doc 13 §5.3 reproduit exactement, cas Bolt autoliquidation testé),
> vraie réconciliation (montant ±1 centime, fenêtre de date, libellé), vraie
> clôture simplifiée (compte de résultat + bilan qui s'équilibre : trésorerie
> = résultat + TVA à payer). Le « reste des transactions » (carburant,
> péage...) passe par règles + ML existant (`categorize/`), accepté sans
> revue humaine (`workflow/auto_accept.py` — stand-in, pas l'architecture
> cible). Postgres + Alembic montés et vérifiés contre un vrai conteneur,
> pas encore branchés dans `demo.py` (qui tourne en mémoire). **Aucun accès
> réel** aux API Digifactory/Rollee (token 401, sandbox non vérifié).
> `documents`, `anomaly`, `ml` n'ont toujours que leur `README.md` +
> `__init__.py`. **Doc 17 semaines 0 à 4 toutes faites** (2026-09-05) :
> semaine 4 tourne sur 3 vrais dossiers (`demo_multi_dossiers.py`) et a fait
> remonter un vrai bug (11/12 règles du pack sans indicateur insensible à la
> casse — le CA détecté d'un dossier passe de 591 € à 11 937 € une fois
> corrigé). Ajouté hors plan initial, demandé explicitement : overlay sur le
> vrai formulaire CERFA 2065-SD officiel (ADR-006) et exports FEC/grand
> livre/balance (doc 06 §6) — le détail légal derrière les chiffres de la
> liasse, pour un contrôle ou pour tracer une erreur.

## Faire tourner la démo (doc 17 semaines 0-3 + CERFA 2065)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m axelcompta.demo
# → liasse.pdf, cerfa_2065.pdf, journal.fec.txt, grand_livre.csv, balance.csv
# dans backend/_demo_output/
```

Aucune base de données requise : `demo.py` utilise `InMemoryLedgerService`.
La couture prouvée : fixtures (settlement Uber 1 040,00 € / transaction
+848,00 € UBER BV, + deux transactions « reste » : carburant, péage) →
`reconcilier()` (doc 13 §4.2) → écriture ventilée TVA pour le settlement
(`construire_ecriture_settlement`, doc 13 §5.3) ou écriture catégorisée pour
le reste (règles + ML via `RulesAndMlPipeline`, puis
`construire_ecriture_categorisee`) → `ClotureSimplifieeService` (compte de
résultat + bilan, doc 17 semaine 3) → deux renderers au choix :
`PdfLiasseSimplifieeRenderer` (lisible, pas de mise en page officielle) ou
`PdfCerfa2065Renderer` (résultat, exercice, régime, comptabilité
informatisée remplis sur le vrai formulaire officiel — identité
d'entreprise volontairement blanche). Vérifié : le bilan s'équilibre
(trésorerie = résultat + TVA à payer), la somme des soldes de tous les
comptes vaut exactement 0, et "728,15" apparaît bien dans la vraie case du
vrai PDF officiel (relu visuellement).

## Faire tourner la démo sur un vrai dossier complet (doc 17 §2, §7bis)

Le run ci-dessus tourne sur 3 transactions (golden test). Pour voir la
chaîne tenir sur un vrai dossier — 543 transactions réelles, exercice 2024
complet, résultat négatif (déficit) :

```bash
.venv/bin/python -m axelcompta.demo_dossier_reel
# → backend/_demo_output/liasse_dossier_reel.pdf
# → backend/_demo_output/cerfa_2065_dossier_reel.pdf (case Déficit remplie)
```

Nécessite le CSV audit (`_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv`,
gitignored — présent sur ce poste, pas forcément sur un clone frais). Voir
doc 17 §7bis pour le détail, dont un vrai bug de mapping compte-par-catégorie
trouvé en construisant ce test (corrigé, pas juste noté).

## Postgres + Alembic

```bash
# DATABASE_URL doit être définie (voir ../.env.example — déjà alignée par
# défaut sur docker-compose.yml, ne pas écraser un .env existant)
docker compose up -d --wait db   # --wait : bloque jusqu'au healthcheck OK
                                  # (sans --wait, "Started" ≠ prêt à accepter
                                  # des connexions — Postgres redémarre en
                                  # interne juste après le premier lancement)
.venv/bin/alembic upgrade head
docker compose down -v           # arrête et supprime les données (dev only)
```

Le schéma (`dossiers`, `ecritures`, `lignes_ecriture`) est défini par module
(`tenants/orm.py`, `ledger/orm.py`) sur une `MetaData` partagée
(`core/db.py`) ; `migrations/env.py` lit `DATABASE_URL` (jamais une valeur
figée dans `alembic.ini`). `PostgresLedgerService` (`ledger/repository.py`)
est l'implémentation réelle de `LedgerService` contre cette base — testée en
intégration (voir plus bas), pas encore branchée dans `demo.py`.

## Reproduire les vérifications

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                       # suite rapide (doc 08 §4 étape 5), sans DB
.venv/bin/mypy axelcompta tests migrations  # strict, doit rester à 0 issue
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/lint-imports                     # frontières de dépendance (doc 03 §3)
```

Pour l'intégration (doc 08 §4 étape 6, nécessite Postgres — voir ci-dessus) :

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/axelcompta_dev"
.venv/bin/pytest -q -m integration
```

**Mise à jour 2026-09-08** : `pytest`, `ruff check .` et `lint-imports`
passent à 0 erreur (182 tests rapides). **Deux écarts pré-existants
trouvés en vérifiant, non corrigés ici (hors scope du lot en cours)** :
`mypy axelcompta tests migrations` remonte 16 erreurs dans des fichiers de
test non liés à ce lot (`test_chauffeurs_demo.py`,
`test_demo_chauffeurs_type.py` — `mypy axelcompta` seul, sans `tests`,
reste propre) ; `ruff format --check .` remonte 4 fichiers jamais
reformatés. La mention « 0 erreur » ci-dessous date du 2026-09-05 et
n'est plus exacte sur ces deux points précis — à traiter séparément.

## Tests : un dossier miroir par module (doc 08 §3)

`tests/<module>/` reproduit exactement `axelcompta/<module>/` — c'est une
règle vérifiée, pas seulement une convention : `tests/test_code_quality.py`
fait échouer `pytest` si un module de `axelcompta/` n'a pas son dossier de
tests miroir avec au moins un `test_*.py`, ou si une fonction dépasse 60
lignes (doc 08 §1 règle 4). Ajouter un module = ajouter son dossier de tests
dans le même commit.

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
| [`packs/`](axelcompta/packs/README.md) | Packs métier : taxonomies, règles, templates | Actif (règles + mapping compte) | Actif |
| [`ingestion/providers/`](axelcompta/ingestion/providers/README.md) | Interface `DataProvider` + implémentations | Actif | Actif |
| [`documents/`](axelcompta/documents/README.md) | Justificatifs, OCR, Factur-X, matching | Non prévu | Actif |
| [`categorize/`](axelcompta/categorize/README.md) | Pipeline règles → ML → LLM → revue humaine | Actif (règles + ML, pas de LLM) | Actif |
| [`anomaly/`](axelcompta/anomaly/README.md) | Détection d'abus / anomalies | Non prévu | Actif |
| [`ledger/`](axelcompta/ledger/README.md) | ❤️ Moteur comptable pur | Actif | Actif |
| [`closing/`](axelcompta/closing/README.md) | Clôture d'exercice, états financiers | Actif (compte de résultat + bilan simplifiés) | Actif |
| [`filings/`](axelcompta/filings/README.md) | Renderers FEC, PDF, EDI-TDFC, INPI | Actif (liasse simplifiée + overlay CERFA 2065 partiel) | Actif |
| [`workflow/`](axelcompta/workflow/README.md) | Validation, revue, signature électronique | Réduit (auto-accept, pas de revue) | Actif |
| [`api/`](axelcompta/api/README.md) | Routes FastAPI, auth, permissions | Réduit (pas d'auth) | Actif |
| [`ml/`](axelcompta/ml/README.md) | Entraînement, évaluation, registry modèles | Non prévu (modèle déjà entraîné réutilisé) | Actif |

## Ce qui existe déjà et sera réutilisé (hors de cet arbre)

Le travail d'audit dans [`_AUDIT_DONNEES/`](../_AUDIT_DONNEES/README.md) n'est
pas dupliqué ici : `packs/` et `categorize/` s'y réfèrent directement (pack
VTC, modèle TF-IDF entraîné, CSV FEC labellisé). Voir [doc 17 §4bis](../docs/17-plan-demo-backend.md#4bis-ce-quon-réutilise-déjà-accélérateurs-issus-de-laudit).
