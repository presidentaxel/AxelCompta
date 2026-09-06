# 17 — Plan de démo produit (UX + moteur réel)

> **Statut : plan de sprint révisé, remplace la version précédente de ce
> doc.** Pivot décidé avec Louis le 2026-09-06 : l'ancien plan (« coupe
> verticale backend, front minimal en semaine 4 ») est **faux maintenant**.
> Le principe change : on construit d'abord le parcours complet des deux
> interfaces produit (gestionnaire PC, chauffeur mobile — détail dans
> [doc 19](19-parcours-utilisateur.md)), avec de **vrais calculs** tournant
> sur un **jeu de données synthétique mais réaliste**, plutôt que l'inverse.
> Le travail déjà fait sur le moteur (§12) n'est pas jeté — il devient le
> cœur qu'on branche derrière ces deux interfaces.
> Dernière mise à jour : 2026-09-06.

## 1. Objectif de la démo

Faire tourner **le produit dans son ensemble** — pas juste le backend — sur
2-3 dossiers chauffeur fabriqués à la main mais crédibles : interface
gestionnaire (PC) + interface chauffeur (mobile) + moteur de calcul réel
(réconciliation, catégorisation, écritures, clôture, liasse). L'objectif
n'est pas la conformité DGFiP ni la gestion de tous les cas limites — c'est
de pouvoir dire **« ça marche, il reste à affiner »**, pas **« c'est un
jouet »**. Citation de Louis (2026-09-06) qui résume l'esprit : *« la démo
est un peu un produit final mais sans la précision de tout, donc tout
marche mais le résultat a le droit d'être un poil foireux »*.

## 2. Ce qui change par rapport à l'ancien plan

| Avant (jusqu'au 2026-09-05) | Maintenant |
|---|---|
| Coupe verticale backend d'abord, front minimal en dernier (rapport HTML) | UX des deux interfaces d'abord, moteur branché dessus dès que possible |
| Données = replay du CSV audit réel (36 152 lignes, bruit réel) | Données = 2-3 chauffeurs type fabriqués à la main (§4), propres mais réalistes |
| Calculs acceptés « estimés/simplifiés » | Calculs **réels** — objectif explicite : détecter si le moteur déconne, sur des données qu'on maîtrise |
| Chauffeur = jamais mentionné (front) | Chauffeur = une des deux interfaces de la démo (doc 19) |
| Connexion bancaire = Digifactory uniquement | Deux modes visibles, un seul câblé en priorité (doc 19 §4) |

**Ce qui ne change pas** : le moteur déjà construit (§12) n'est pas
réécrit — reconciliation, catégorisation, écritures, clôture, liasse
gardent leur logique. Ce qui change, c'est le jeu de données qu'on leur
donne à manger, et le fait qu'on les branche derrière une vraie interface
plutôt qu'un rapport HTML de sortie.

## 3. Principe directeur (mis à jour)

**Le parcours utilisateur d'abord, le moteur dessous dès que possible.**
On ne construit pas une UI seule sur des données statiques mockées jusqu'au
bout — dès qu'un écran existe, on le branche sur le vrai moteur (déjà
construit) plutôt que d'attendre la fin. Le risque principal n'est plus
l'intégration technique (déjà prouvée, doc 17 historique §12) mais
**est-ce que le parcours donne envie et est-ce que le calcul reste juste
sur un cas qu'on maîtrise**.

## 4. Le jeu de données synthétique — 3 chauffeurs type

Fabriqués à la main pour être crédibles (volume, variété) sans tomber dans
les vrais cas limites du dataset historique (doc 07). Chacun exerce un
chemin de calcul déjà implémenté (§12) — aucun nouveau template à écrire,
seulement de nouvelles données à faire tourner dedans. Objectif explicite
de Louis : *« il faut 2/3 chauffeurs un peu différents, on veut voir
comment ça rend en gestion multicompte de façon claire »*.

### 4.1 Karim — SASU, IS, assujetti TVA (taux réduit 10%), Uber principalement

Le cas « propre » : le golden test déjà validé (doc 13 §5.3) devient son
mois type, répété sur 4 semaines avec de légères variations de volume.

```
Semaine type (× 4, montants variables ±15%) :
  Settlement Uber : brut 1 040,00 € TTC / commission 192,00 € TTC / net 848,00 €
  → 512 D 848,00 / 622x D 160,00 / 44566 D 32,00 / 706 C 945,45 / 44571 C 94,55
Charges du mois : carburant (~4× 55-70 €, Esso/Total), péage (~4× 8-12 €),
assurance auto (1× mensuelle), entretien (1× ponctuel, ex. Norauto).
Repas légitimes hors domicile (2-3× dans le mois) : McDonald's/Quick — pas
présumés personnels (doc 07 §4, BOFiP).
```

Sert de golden test **et** de "dossier de référence sans ambiguïté" pour
montrer que le cas nominal ne fait pas remonter de fausse alerte.

### 4.2 Sophie — EURL, IS, assujetti TVA, Uber + Bolt, une dépense personnelle ambiguë

Teste le mix de plateformes (autoliquidation Bolt, doc 13 §5.3 « cas
autoliquidation ») et la file de revue humaine :

```
Semaines paires : settlement Uber (comme Karim, montants différents).
Semaines impaires : settlement Bolt — commission HT 160,00 €, autoliquidation
  UE : 44566 D 32,00 / 44571 C 32,00 (impact trésorerie nul, obligatoire
  pour la CA3, doc 13 §5.3).
Une dépense carte pro à consonance personnelle dans le mois (ex. achat Zara
ou Sephora, ~60-80 €) — doit remonter dans la file de revue comme
« à justifier / usage personnel » (doc 06 §3.6, doc 11 §3.2), pas être
auto-acceptée. Sert à montrer que le pipeline distingue le nominal de
l'à-trancher, pas seulement à calculer juste.
```

### 4.3 Yanis — franchise TVA, Uber uniquement, véhicule en LOA

Teste le régime franchise (pas de TVA collectée, doc 13 §5.3 « cas
franchise ») et le financement en LOA (doc 06 §3.5). **Uber, pas Bolt** :
combiner franchise et commission en autoliquidation UE (Bolt) pose une
vraie question fiscale (l'obligation d'autoliquider peut subsister malgré
la franchise) volontairement laissée hors scope démo — seule la
combinaison franchise + `france_20` est implémentée (§5).

```
Settlement Uber : brut 1 040,00 € (pas de TVA collectée), commission
  192,00 € TTC non récupérable (franchise) :
  512 D 848,00 / 622x D 192,00 (TTC) / 706 C 1 040,00
Loyer LOA mensuel (378 € TTC) : passé en 613 (locations) via la
catégorisation courante — pas de split déductible/non déductible pour cette
démo (doc 06 §3.5 : la ventilation fine reste V1, hors scope §8).
```

### 4.4 Ce que ces trois profils prouvent ensemble

Trois régimes TVA (assujetti/franchise), les deux plateformes du pilote
avec leurs deux traitements TVA différents, un cas nominal, un cas à
trancher par un humain, un cas avec immobilisation financée — sans sortir
une seule fois du périmètre déjà documenté et déjà codé. C'est le test de
« gestion multicompte claire » demandé : le gestionnaire doit voir au
premier coup d'œil que ces trois dossiers sont dans des états différents.

## 5. Le moteur réutilisé tel quel

Rien ne change dans la logique de calcul déjà construite (détail complet
en §12 et [doc 18](18-organisation-code.md)) :

| Module | Rôle | Statut |
|---|---|---|
| `ingestion/reconciliation.py` | Matching settlement ↔ transaction bancaire | Fait, inchangé |
| `ingestion/ecritures_settlement.py` | Ventilation TVA Uber/Bolt/franchise | Fait — **étendu le 2026-09-06** : `tva_recettes_regime` en paramètre, franchise ajoutée (§9 semaine 1) |
| `categorize/rules_and_ml.py` | Règles pack VTC + modèle ML pour le reste des transactions | Fait, inchangé |
| `workflow/auto_accept.py` | Stand-in pour la revue humaine (démo seulement) | Fait — **remplacé dans la démo produit** par la vraie file de revue humaine (doc 11 §3.1) côté UI, puisque Sophie (§4.2) doit être tranchée par un humain, pas auto-acceptée |
| `closing/bilan_simplifie.py`, `filings/*` | Clôture, liasse, CERFA 2065, FEC, grand livre, balance | Fait, inchangé |

Seul `workflow/auto_accept.py` change de rôle : il servait de bouchon
d'auto-validation en l'absence d'UI ; la démo produit a maintenant une
vraie file de revue humaine à montrer, donc le stub n'est plus la solution
pour tous les cas — seulement un fallback si le temps manque pour brancher
l'écran de revue derrière chaque profil.

## 6. Les deux interfaces de la démo

Détail complet du parcours dans [doc 19](19-parcours-utilisateur.md). Pour
la démo précisément :

- **Interface gestionnaire (PC/web)** : dashboard des 3 dossiers, file de
  revue réelle sur la dépense ambiguë de Sophie, clôture et liasse par
  dossier — s'appuie directement sur doc 11, rien de nouveau à concevoir
  côté écrans, seulement à construire.
- **Interface chauffeur (mobile/webapp)** : au moins un des trois profils
  (Karim, le plus simple) doit pouvoir être suivi côté chauffeur — voir ses
  transactions catégorisées, répondre à une question simple, signer.

## 7. Connexion bancaire dans la démo

Voir [doc 19 §4](19-parcours-utilisateur.md#4-connexion-bancaire--deux-modes-par-dossier).
Résumé : mode `gestionnaire` (Digifactory) câblé en priorité — Louis
relance le fournisseur pour débloquer le token 401 (doc 16 §7) avant la fin
du mois. Mode `chauffeur_direct` : **si le temps le permet**, montré en
fonctionnement à la fin plutôt qu'en premier — pas bloquant pour juger la
démo réussie.

## 8. Coupes de scope assumées (mise à jour)

Ce qui reste hors scope, comme avant :
- Multi-tenant / RLS complet (les 3 dossiers de démo suffisent, un seul
  schéma).
- OCR réel des justificatifs (la photo s'attache à la transaction, le
  contenu n'est pas lu).
- Détection d'anomalies statistique (doc 05 §6.2) — la dépense ambiguë de
  Sophie est un cas écrit à la main, pas détectée par un modèle de profil.
- Signature électronique réelle (prestataire non choisi, ADR-004 toujours
  en attente) — simulateur d'écran suffit.
- Matrice complète statut × pack — seulement les 3 profils ci-dessus.

Nouveau, ajouté par ce pivot :
- **Pas de self-signup public** (doc 19 §3.1) — les comptes de démo sont
  créés à la main.
- **Pas de synchronisation API gestionnaire** (doc 19 §3.3) — prévue,
  documentée, pas construite ici.
- **Pas de app store réel** — la démo tourne en webapp, l'app native est un
  objectif post-démo (doc 19 §7).

## 9. Semaines et jalons

Repart de la coupe verticale déjà prouvée (§12) — on ne recommence pas de
zéro, on ajoute les deux interfaces autour du moteur existant.

### Semaine 1 — Jeu de données + branchement moteur

- Écrire les fixtures des 3 profils (§4) comme `NormalizedTransaction` +
  `PlatformSettlement`, au format déjà attendu par les providers existants.
- Vérifier que le moteur existant (§5) tourne sans modification dessus —
  seul un bug de mapping/règle serait acceptable à corriger (comme les deux
  déjà trouvés en semaine 4 de l'ancien plan, §12).

> **Fait (2026-09-06)** — `backend/axelcompta/ingestion/providers/chauffeurs_demo.py`
> (génération déterministe des 3 profils : courses agrégées en settlements
> hebdomadaires, dépenses récurrentes, la dépense ponctuelle de Sophie) et
> `backend/axelcompta/demo_chauffeurs_type.py` (composition root : rapport
> HTML + liasse/CERFA/FEC/grand livre/balance par chauffeur, sur le modèle
> de `demo_multi_dossiers.py`). Contrairement à `demo_dossier_reel.py`,
> aucun fichier gitignored requis — tourne sur n'importe quel clone.
>
> Le moteur n'a **pas** tourné sans modification, contrairement à
> l'hypothèse ci-dessus — écart trouvé en écrivant Yanis (franchise) plutôt
> qu'en testant après coup : `ingestion/ecritures_settlement.py` avait le
> taux de TVA recettes figé en dur à 10% assujetti (profil unique de
> l'ancien plan, doc 17 §3 d'origine) et ne savait pas du tout traiter la
> franchise. Ajouté `tva_recettes_regime` en paramètre (doc 13 §5.1,
> vocabulaire doc 14 §1.2) avec la branche franchise déjà décrite doc 13
> §5.3 — limitée à une commission `france_20` (§4.3). Une deuxième règle
> manquante trouvée pareillement : le pack réduit (12 règles) n'avait pas
> de règle LOA, ajoutée dans `_AUDIT_DONNEES/packs_vtc/regles_regex.csv`
> (donnée, pas du code). Les deux ont des tests dédiés
> (`tests/ingestion/test_ecritures_settlement.py`,
> `tests/ingestion/providers/test_chauffeurs_demo.py`).
>
> Résultat sur les 3 profils (200 jours actifs chacun, ~230 jours
> calendaires, seed déterministe) : 100% des settlements réconciliés,
> toutes les écritures équilibrées. CA plateforme sur la période : Karim
> 14 412 €, Sophie 13 375 € (Uber+Bolt), Yanis 12 584 € (franchise). Le
> compte d'attente 471 de Sophie contient bien la dépense Zara (68 €), pas
> auto-catégorisée sur un compte de résultat (doc 17 §11).

### Semaine 2 — Interface gestionnaire

- Dashboard 3 dossiers + fiche dossier (doc 11 §2) branchés sur les vraies
  données des 3 profils.
- File de revue réelle (doc 11 §3.1) sur la dépense ambiguë de Sophie —
  premier écran qui remplace un stub du moteur (`auto_accept`) par une
  vraie décision humaine dans l'UI.

### Semaine 3 — Interface chauffeur

- Parcours mobile de Karim (doc 19 §5) : transactions, une question de
  catégorisation, signature.
- Connexion bancaire mode `gestionnaire` visible (toggle) ; mode
  `chauffeur_direct` en construction si le temps le permet (§7).

### Semaine 4 — Clôture, liasse, tampon, répétition

- Clôture + liasse + CERFA 2065 + FEC/grand livre/balance sur les 3
  dossiers (déjà fait au niveau moteur, §12 — reste à les exposer dans
  l'interface gestionnaire plutôt qu'un export PDF isolé).
- Répétition avec un run pré-cuit en secours, comme dans l'ancien plan.

## 10. Risques et mitigations

| Risque | Mitigation |
|---|---|
| Token Digifactory toujours bloqué fin de mois | Le mode `gestionnaire` de la démo tourne sur les fixtures des 3 profils, pas sur l'API réelle — la relance Digifactory est en parallèle, pas sur le chemin critique de la démo |
| Vouloir montrer `chauffeur_direct` complet fait déraper le planning | Explicitement en dernier, explicitement optionnel (§7, §9 semaine 3) |
| La vraie file de revue humaine (nouveau vs `auto_accept`) prend plus de temps que prévu | Fallback : garder `auto_accept` pour Karim/Yanis (cas nominaux), ne construire l'écran de revue que pour le cas Sophie qui le justifie |
| Dérive de scope vers la matrice complète statut × pack | §8 rappelle explicitement les non-objectifs |

## 11. Golden tests

Le golden test Uber existant (doc 13 §5.3, ancien §7 de ce doc) reste valide
tel quel — c'est exactement le mois type de Karim (§4.1). S'y ajoutent
deux golden tests supplémentaires, un par nouveau profil :

- **Sophie** : le mois complet doit produire une écriture usage-personnel
  (455/108) sur la dépense ambiguë **uniquement après validation humaine**
  dans la file de revue — pas d'auto-acceptation sur ce cas précis.
  **Vérifié côté moteur (2026-09-06)** : la dépense reste au compte
  d'attente 471, jamais auto-catégorisée (`tests/test_demo_chauffeurs_type.py`)
  — la vraie écriture 455/108 reste à faire une fois la file de revue
  construite côté UI (§9 semaine 2).
- **Yanis** : balance équilibrée avec le traitement franchise (pas de TVA
  collectée). **Fait (2026-09-06)** : `tests/ingestion/test_ecritures_settlement.py`
  et `tests/ingestion/providers/test_chauffeurs_demo.py`. Le suivi LOA
  hors-bilan (part non déductible séparée) n'est pas fait — la démo passe
  le loyer en charge simple (613), limite assumée (§4.3).

## 12. Historique — ce qui a déjà été fait (acquis, réutilisé §5)

L'ancien plan (semaines 0 à 4, du 2026-09-01 au 2026-09-05) a démontré que
la chaîne complète tient bout-en-bout sur données réelles, avant ce pivot :

- **Semaine 0** : squelette bout-en-bout, PDF produit en mémoire, Postgres/
  Alembic montés (pas encore branchés).
- **Semaine 1** : les 5 providers fonctionnels ; `FileImportProvider`
  rejoue le CSV audit réel (36 152 lignes).
- **Semaine 2** : réconciliation réelle (doc 13 §4.2), écritures ventilées
  TVA Uber/Bolt (doc 13 §5.3), règles + ML pour le reste.
- **Semaine 3** : clôture réelle (bilan qui s'équilibre), liasse simplifiée
  en PDF.
- **Hors plan initial** : overlay sur le vrai CERFA 2065-SD officiel
  (`filings/cerfa_2065.py`).
- **Semaine 4** : tourné sur 3 vrais dossiers du CSV audit (pas des
  fixtures) — **deux vrais bugs trouvés** : règles regex non insensibles à
  la casse (CA détecté passé de 591 € à 11 937 € une fois corrigé), mapping
  `recettes_plateformes` sur un mauvais compte.
- **Test dossier réel complet** (`demo_dossier_reel.py`) : un vrai exercice
  2024 rejoué (543 transactions), résultat négatif, case Déficit du CERFA
  2065 exercée pour la première fois.
- **Hors plan initial** : exports FEC + grand livre + balance
  (`filings/fec.py`, `filings/export_comptable.py`).

Détail complet, fichier par fichier, commandes de reproduction :
[doc 18](18-organisation-code.md) et [backend/README.md](../backend/README.md).
**Rien de ce travail n'est perdu** — c'est le contenu du §5 ci-dessus.

## 13. Rappel — ce plan n'est pas le roadmap

Les hypothèses de capacité, les phases et les critères de sortie du doc 12
restent la référence pour la trajectoire produit réelle. Ce doc 17 est un
sprint de preuve de concept isolé, pas une réduction du périmètre V1.
