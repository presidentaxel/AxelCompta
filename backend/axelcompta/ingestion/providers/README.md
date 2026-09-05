# ingestion/providers/

Le pattern `DataProvider` : toute source de données d'entrée (banque,
plateforme gig) implémente la même interface abstraite. La configuration du
dossier détermine quels providers sont actifs — **le code métier en aval ne
connaît jamais le provider concret**.

**Dépendances :** `core`, `tenants` (config dossier).

## Providers V1

- `DigifactoryProvider` — transactions bancaires (agrège Bridge par contact).
- `RolleeProvider` — settlements plateformes gig (Uber, Bolt…).
- `FileImportProvider` — CSV/XLSX/ODS.
- `BridgeProvider` direct — piste parallèle non bloquante, pas de
  développement actif tant que Digifactory couvre le besoin.

## Les trois chemins pour la démo (doc 17 §4-5)

Le token Digifactory est en 401 à ce jour (doc 16 §7) et l'accès sandbox
Rollee n'a pas encore été testé — la démo doit donc pouvoir tourner sans
dépendre d'aucune des deux API externes le jour J :

| Chemin | Provider bancaire | Provider settlement |
|---|---|---|
| A (réel) | `DigifactoryProvider` si déblocage token | `RolleeProvider` si accès sandbox obtenu |
| B (fixtures) | `DigifactoryProvider` contre fixtures (schéma doc 16 §3-4) | `PlatformSettlement` fixtures calées main sur les mêmes transactions (doc 13 §4.1) |
| C (filet, banque seulement) | `FileImportProvider` rejouant `_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv` (48 042 lignes réelles labellisées) | — |

Les trois passent par la même interface — zéro changement ailleurs dans le
pipeline selon le chemin retenu le jour de la démo.

## Statuts

- **Démo (doc 17 semaine 0, fait)** : `FixtureProvider`/`FixtureSettlementProvider`
  rendent les données du golden test doc 17 §7 (settlement Uber 1 040,00 € /
  transaction +848,00 € UBER BV). **Semaine 1 (à faire)** : chemins A/B/C
  réels pour `DigifactoryProvider`/`RolleeProvider`/`FileImportProvider`
  (aujourd'hui des stubs qui lèvent `NotImplementedError`).
- **V1 (doc 12, phase 0.3 + 1)** : spikes Digifactory/Bridge/Rollee menés à
  terme, tous les chemins de secours consolidés.

## Doc de référence

[doc 03 §3](../../../../docs/03-architecture.md#3--découpage-en-modules-monolithe-modulaire) (pattern DataProvider),
[doc 13](../../../../docs/13-integrations-plateformes.md) (détail complet du pattern + Rollee),
[doc 16](../../../../docs/16-integration-digifactory.md) (Digifactory),
[doc 17 §4-5](../../../../docs/17-plan-demo-backend.md#4-filet-de-sécurité--ingestion-bancaire-digifactorybridge).
