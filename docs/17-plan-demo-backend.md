# 17 — Plan démo backend accéléré (1 mois, optimiste)

> **Statut : plan de sprint, volontairement optimiste et non réaliste.**
> Distinct du roadmap (doc 12), qui reste l'hypothèse de référence à capacité
> réelle (1-2 devs, phases pluri-mensuelles). Ce doc-ci sert un seul objectif :
> une démo interne — **pas client** — prouvant que la chaîne complète tient
> bout-en-bout. Aucune gestion des cas limites n'est visée ; le concept est
> considéré validé dès qu'un dossier passe de l'ingestion à la liasse sans
> intervention manuelle sur le chemin nominal.
> Dernière mise à jour : 2026-09-01.

## 1. Objectif de la démo

Partir d'une ingestion Digifactory/Bridge (ou son filet de secours, §4) **et**
d'une réconciliation Rollee réelle (§5, **must-have**, pas de mode dégradé),
et produire automatiquement une liasse fiscale sur 1-3 dossiers de test. Le
front n'est pas la priorité (§6, semaine 4 seulement, minimal).

## 2. Principe directeur

**Coupe verticale d'abord.** Faire tourner tout le pipeline bout-en-bout dès
les premiers jours avec des données bidons/fixtures, puis remplacer les
bouchons un par un par du réel. On ne finit jamais un module en profondeur
avant que la couture vers le suivant existe — l'intégration est le risque
principal sur un mois, pas la justesse d'un module isolé.

## 3. Coupes de scope assumées

Un seul profil dossier, codé en dur, tout le reste dérive de là :

- **SASU, IS, TVA réel normal, assujetti 10% sur recettes, pas d'option IR, pas de franchise.**
- 2-3 dossiers de démo max, pas 200.
- Catégorisation : règles + modèle ML déjà entraîné (§4bis). **Pas de LLM
  d'arbitrage** dans la démo (stub qui passe tout en confiance haute).
- Liasse : sous-ensemble de formulaires (bilan simplifié + compte de résultat
  + une case-clé 2065), rendu en PDF propre — **pas de conformité CERFA/DGFiP
  stricte**, pas d'EDI, pas d'INPI.

**Ce qu'on ne construit pas du tout pour cette démo :**

- Multi-tenant / RLS (un seul schéma suffit)
- Auth / MFA (accès direct ou trivial)
- OCR / justificatifs (transactions traitées sans matching de pièce)
- Détection d'anomalies
- Workflow de revue humaine / UI de validation
- Signature électronique
- Dashboard consentements
- Entraînement ML (on réutilise le modèle existant, §4bis)
- Matrice statut × pack (doc 03 §3bis, doc 06 §7) — un seul profil en dur

## 4. Filet de sécurité — ingestion bancaire (Digifactory/Bridge)

Le token Digifactory est en 401 à ce jour (doc 16 §7) — ne pas parier la
démo dessus seul.

- **Chemin A** : `DigifactoryProvider` réel si le token se débloque d'ici là.
- **Chemin B** : fixtures Digifactory (schéma doc 16 §3-4) si toujours bloqué.
- **Chemin C (filet)** : rejouer `resultats/fec_ml_taxonomie.csv` (36 152
  lignes réelles déjà labellisées à ce jour — 48 042 avant une passe de
  réduction du bucket non catégorisé, chiffre resté dans le §4bis et
  ADR-007 pour le benchmark ML historique) via `FileImportProvider` —
  **fait** (semaine 1) : regroupe les lignes composites, inverse la
  convention débit-crédit FEC vers le sens relevé bancaire, testé contre le
  fichier réel. Garantit que la démo ne meurt pas si l'API externe est
  capricieuse le jour J, et prouve le pipeline sur données réelles quoi
  qu'il arrive.

Les trois passent par la même interface `DataProvider` (doc 03 §2.2,
doc 13 §2) — zéro changement ailleurs dans le pipeline selon le chemin retenu
le jour de la démo.

## 4bis. Ce qu'on réutilise déjà (accélérateurs issus de l'audit)

Ce plan tient en un mois en grande partie parce que ces briques existent déjà :

| Actif | Où | Usage démo |
|---|---|---|
| `packs_vtc/` — 24 règles regex, 61 mappings PCG, 18 catégories | `_AUDIT_DONNEES/packs_vtc/` | Base du catégoriseur à règles, réduite aux ~15 catégories les plus fréquentes |
| `resultats/fec_ml_taxonomie.csv` — 36 152 lignes labellisées | `_AUDIT_DONNEES/resultats/` | Filet d'ingestion (chemin C, **fait**) + jeu de données pour le golden test |
| `modeles/tfidf_logreg_v1.joblib` — 94,4% accuracy | `_AUDIT_DONNEES/modeles/` | Fallback ML pour ce que les règles ratent, aucun réentraînement nécessaire |
| Exemple chiffré Uber France / Bolt déjà travaillé | doc 13 §5.3 | Sert directement de golden test de réconciliation + ventilation TVA (§7) |

## 5. Rollee — réconciliation réelle (must-have, pas de mode dégradé)

Contrairement à une version précédente de ce plan, **on ne bascule pas sur le
mode dégradé** de doc 13 §6 (écriture `512/706` brute sans ventilation). La
démo doit montrer l'algorithme de matching (doc 13 §4.2) et la génération
d'écriture ventilée (doc 13 §5.3) — c'est la partie qui démontre la valeur
du produit.

**Risque à lever en priorité, jour 1 :** le statut d'accès au sandbox Rollee
n'est pas connu à ce stade (contrairement à Digifactory, aucun test d'accès
n'a encore été fait côté Rollee). Vérifier ça avant toute autre chose cette
semaine — c'est potentiellement le même genre de blocage que le 401
Digifactory, découvert cette fois avant de compter dessus plutôt qu'après.

- **Chemin A** : `RolleeProvider` réel contre le sandbox si l'accès est obtenu à temps.
- **Chemin B (filet)** : fixtures `PlatformSettlement` construites à la main
  selon le schéma doc 13 §4.1, **calées sur les mêmes transactions bancaires**
  choisies pour la démo (même montant net, même fenêtre de date) — pour
  garantir que la réconciliation ait un match propre à montrer, même sans
  API Rollee fonctionnelle. Contrairement au côté bancaire, il n'existe pas
  de dataset Rollee déjà réel/labellisé dans l'audit ; ces fixtures sont donc
  à écrire spécifiquement pour la démo, pas récupérables gratuitement.

## 6. Semaine par semaine

### Semaine 0 (jours 1-3) — Squelette bout-en-bout

- `core/` minimal : `Money` (centimes int), types id.
- Postgres + Alembic minimal, un seul schéma.
- **Les deux flux dès le départ** : `FixtureProvider` (transactions bancaires
  bidons) + `FixtureSettlementProvider` (settlements Rollee bidons) →
  réconciliation bouchon (match trivial) → écriture bouchon → clôture bouchon
  → PDF "Hello World" liasse.
- Objectif : une commande unique produit un PDF, même avec des chiffres faux.
  Valide les coutures avant d'investir dans la justesse — y compris la
  couture réconciliation, qui est la plus risquée.
- **Jour 1, en parallèle** : vérifier l'accès sandbox Rollee (§5) et relancer
  le fournisseur Digifactory sur le token (§4).

### Semaine 1 — Ingestion réelle des deux côtés

- `DigifactoryProvider` contre fixtures/réel selon déblocage (chemin A/B §4).
- `FileImportProvider` branché sur le CSV audit en filet (chemin C §4).
- `RolleeProvider` réel (chemin A §5) ou fixtures calées main (chemin B §5).
- Normalisation : `Decimal`→centimes à l'ingestion, filtrage `deleted`/`future`
  côté banque (doc 16 §5).

### Semaine 2 — Réconciliation + catégorisation + écritures complètes

> **Fait (2026-09-05)** — `backend/axelcompta/ingestion/reconciliation.py`,
> `ingestion/ecritures_settlement.py`, `categorize/rules_and_ml.py`,
> `workflow/auto_accept.py`. Détail : [docs/18-organisation-code.md](18-organisation-code.md).

- Algorithme de matching montant+date+libellé (doc 13 §4.2), états
  `en_attente_banque` / `réconcilié` / `revue manuelle`.
- Templates d'écriture **avec ventilation TVA complète** (doc 13 §5.3) : au
  minimum le cas Uber France (TVA 20% sur commission, déductible normalement)
  et le cas Bolt (autoliquidation UE) — les deux variantes déjà chiffrées dans
  la doc, pas besoin de les redériver.
- Règles regex du pack VTC (réduites à ~15 catégories) + modèle TF-IDF existant
  en fallback pour le reste des transactions (carburant, péage, entretien...).

### Semaine 3 — Clôture + liasse

- Balance → compte de résultat / bilan simplifié.
- `LiassePivot` réduit au strict nécessaire pour le récit de démo, rendu PDF.
- **Golden test de sortie** (§7) : le critère de "c'est fini", pas la
  conformité DGFiP.

### Semaine 4 — Tampon + démo

- Faire tourner sur 2-3 dossiers pour montrer que ce n'est pas câblé en dur
  sur un seul cas.
- Front minimal, pas prioritaire : un rapport HTML/notebook qui montre les
  étapes du pipeline (transaction → settlement → réconciliation → écriture
  → liasse) plutôt qu'une vraie UI — juste pour le récit visuel de la démo.
- Répétition avec un run pré-cuit en secours si une API externe est capricieuse
  le jour J (les chemins B/filet de §4 et §5 doivent être prêts à être
  rejoués instantanément, pas improvisés en live).

## 7. Golden test de sortie

Reproduire noir sur blanc l'exemple déjà chiffré en doc 13 §5.3 : settlement
Uber 1 040,00 € TTC / commission 192,00 € TTC / net 848,00 €, réconcilié avec
la transaction bancaire `+848,00 € UBER BV`, générant :

```
512   Banque                        D   848,00
622x  Commissions plateformes       D   160,00
44566 TVA déductible sur commission D    32,00
706   Prestations de services       C   945,45
44571 TVA collectée (10%)           C    94,55
```

Balance équilibrée, écriture visible dans le grand livre du dossier,
apparaît dans la liasse générée. Si ce cas précis tourne sur un dossier de
démo (réel ou fixture calée), le concept est considéré validé.

## 8. Risques et mitigations

| Risque | Mitigation |
|---|---|
| Token Digifactory toujours bloqué (401, doc 16 §7) | Chemin B (fixtures) ou C (replay FEC) — déjà prévu, pas un blocage de dernière minute |
| Accès sandbox Rollee jamais vérifié à ce jour | Vérifier jour 1 ; fixtures calées main en filet (§5 chemin B) |
| Réconciliation qui ne matche rien en démo live | Répétition avec run pré-cuit (semaine 4), ne pas dépendre du direct |
| Dérive de scope (retomber sur la matrice statut × pack, le multi-tenant...) | §3 rappelle explicitement les non-objectifs ; toute demande hors profil unique est reportée au doc 12 |

## 9. Rappel — ce plan n'est pas le roadmap

Les hypothèses de capacité, les phases et les critères de sortie du doc 12
restent la référence pour la trajectoire produit réelle. Ce doc 17 est un
sprint de preuve de concept isolé, pas une réduction du périmètre V1.
