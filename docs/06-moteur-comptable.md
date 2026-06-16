# 06 — Moteur comptable (`ledger` + `closing` + `filings`)

> Statut : brouillon à valider — Dernière mise à jour : 2026-06-12

Le module le plus critique du système. C'est lui qui doit être « incassable » :
déterministe, pur, couvert à 100 % par les tests, vérifié par invariants.

## 1. Invariants absolus (violations = bug bloquant, jamais contournable)

| # | Invariant | Vérifié par |
|---|-----------|-------------|
| I1 | Toute écriture est équilibrée : Σ débits = Σ crédits, au centime | Assertion à la création + contrainte d'intégrité + test de propriété |
| I2 | Une écriture validée est **immuable** ; correction = contre-passation référencée | Append-only en base (pas d'UPDATE/DELETE sur les lignes validées, trigger de protection) |
| I3 | Numérotation continue et séquentielle par journal et par exercice | Séquence transactionnelle + test de non-trou |
| I4 | Aucune écriture sur période clôturée | Vérification de période + verrou de clôture |
| I5 | Montants en **centimes entiers** ; aucun flottant dans le module | Type `Money`, lint interdisant `float` dans `ledger/` |
| I6 | Toute écriture référence sa source (transaction, pièce, OD documentée) | Champ obligatoire, non nullable |
| I7 | La balance générale s'équilibre à tout instant t | Test d'intégrité quotidien en prod (job) + après chaque batch |
| I8 | Le FEC exporté repasse les contrôles DGFiP | Test CI sur dossiers de référence |

## 2. Objets du domaine

- **Dossier** : une entité comptable (la société d'un chauffeur, une PME en mode
  mono-entreprise…). Porte le
  paramétrage : statut juridique, régime fiscal (IS/IR, réel simplifié/normal),
  régime TVA (franchise, réel simplifié, réel normal), dates d'exercice, plan de
  comptes, profil de récupération TVA des véhicules.
- **Journaux** V1 : `BQ` (banque), `AC` (achats), `VE` (ventes), `OD` (opérations
  diverses), `AN` (à-nouveaux).
- **Plan de comptes** : PCG embarqué (référentiel versionné par millésime) + comptes
  ouverts par dossier. Un axe **analytique** est disponible par dossier (utile pour
  un dossier multi-activités, ou un futur cas CAE où une coopérative serait un seul
  dossier avec des sections analytiques par entrepreneur-salarié).
- **Écriture** = en-tête (journal, date, libellé, référence pièce, statut) +
  lignes (compte, sens, montant, analytique, code TVA).

## 3. Schémas d'écritures types : la bibliothèque de templates du **pack VTC**

Le passage catégorie → écritures se fait par **templates d'écritures** : des données
versionnées livrées par pack métier (doc 03 §3bis) et paramétrées par dossier
(statut, régime TVA, profil véhicule…). Le pack VTC est le premier ; un futur pack
(commerce, BTP…) apportera ses propres templates sans toucher au moteur — le moteur
ne connaît que la mécanique générique « template + paramètres → écritures
équilibrées ». Exemples du pack VTC qui doivent être parfaits dès la V1 :

### 3.1 Carburant (cas simple, mais piège TVA)
```text
Ticket 60,00 € TTC, gazole, véhicule de tourisme (TVA récupérable à 80 %)
60611  Carburant                          D 52,00
44566  TVA déductible (80 % de 10,00)     D  8,00
60611  Carburant (TVA non récup. 20 %)    D  2,00   ← réintégrée au coût (option : compte dédié)
512    Banque                             C 60,00  (via 401 si facture fournisseur)
```
Paramétrage par dossier/véhicule : essence vs gazole vs électrique, VP vs VU —
les taux de récupération diffèrent et évoluent ; ils vivent dans une **table de
règles fiscales versionnée par année**, pas dans le code.

### 3.2 Achat de véhicule (immobilisation)
```text
Véhicule 25 000 € TTC (VP : TVA non récupérable, incorporée au coût)
2182   Matériel de transport              D 25 000
404    Fournisseurs d'immobilisations     C 25 000
→ crée une fiche IMMOBILISATION : base 25 000, durée 4-5 ans, linéaire,
  prorata temporis 1re année, plafond fiscal d'amortissement VP selon CO2
  (réintégration extra-comptable calculée pour la liasse).
```

### 3.3 Dotation aux amortissements (générée automatiquement à la clôture)
```text
68112  Dotations amort. immos corporelles  D x
28182  Amort. matériel de transport        C x
```
Le plan d'amortissement est calculé à la création de l'immo, recalculé en cas de
cession, et **chaque dotation est rejouable** : mêmes entrées → mêmes montants.

### 3.4 LOA / crédit-bail
```text
Loyer mensuel : 6122 Crédit-bail mobilier D / 512 C (TVA selon véhicule)
+ engagement hors-bilan suivi pour l'annexe
+ part de loyer non déductible (plafond CO2 véhicule de tourisme) calculée
  automatiquement → état de réintégration fiscale pour la liasse.
Levée d'option en fin de contrat → immobilisation à la valeur d'option.
```

### 3.5 Recettes plateformes (Uber, Bolt…) — via Rollee

Le virement bancaire brut (ex. `+848,00 € UBER BV`) est complété par le settlement
Rollee de la même semaine (courses brutes, commission, TVA commission, net). La
réconciliation de ces deux sources produit l'écriture complète. Sans Rollee, une
écriture simplifiée est générée en attendant (doc 13 §6).

**TVA sur recettes — configurable par dossier (`tva_recettes_regime`) :**
- `assujetti_taux_reduit` : transport de personnes = TVA **10%** (taux réduit)
- `franchise` : pas de TVA collectée (montant brut = montant HT)

**TVA sur commissions — configurable par plateforme dans le pack (`packs/vtc/platforms.yaml`) :**
- Uber France SAS : TVA 20% française (déductible normalement)
- Bolt Operations OÜ (Estonie, UE) : autoliquidation art. 283-2 CGI

```text
Exemple : settlement Uber, dossier SASU IS assujetti TVA 10%, Uber France (TVA commission 20%)
  Rollee : gross 1 040,00 € TTC | commission 192,00 € TTC | net 848,00 €

  Recettes HT   = 1 040,00 / 1,10 = 945,45 €
  TVA collectée = 1 040,00 − 945,45 = 94,55 €
  Commission HT = 192,00 / 1,20 = 160,00 €
  TVA commission = 192,00 − 160,00 = 32,00 €

  512    Banque                         D   848,00
  622x   Commissions plateforme (HT)    D   160,00
  44566  TVA déductible commission 20%  D    32,00
  706    Prestations de services (HT)   C   945,45
  44571  TVA collectée 10%              C    94,55
                                        ─────────────
                                        1 040,00 = 1 040,00 ✓
```

Le template est un fichier de données dans `packs/vtc/` paramétré par la
configuration du dossier et de la plateforme — jamais de `if plateforme == "uber"`
dans le code. Voir doc 13 §5 pour tous les cas (franchise TVA, autoliquidation).

### 3.6 Usage personnel confirmé (issue d'une alerte)
```text
Compte déterminé par le statut configuré du dossier : 455 Compte courant d'associé
(SASU/EURL), 108 Prélèvements de l'exploitant (EI). Jamais en charge. Template
déclenché par la résolution d'alerte (doc 05 §6.3).
```

Chaque template est défini en données (pas en code), versionné, et accompagné de
ses cas de test chiffrés.

## 4. Rapprochement bancaire

Particularité du produit : on part des transactions bancaires, donc le 512 est
naturellement alimenté. Le rapprochement consiste à garantir : solde 512 du
grand livre = solde du relevé à toute date de fin de mois. Écarts → liste
d'anomalies (transactions non comptabilisées, doublons, écritures manuelles).
Un dossier ne peut pas être clôturé avec un rapprochement non soldé.

## 5. Clôture d'exercice (`closing`)

Checklist automatisée, chaque étape produisant des écritures OD traçables :

1. Rapprochements bancaires soldés sur 12 mois.
2. Zéro proposition en attente de validation sur l'exercice.
3. Alertes d'anomalies toutes instruites.
4. Dotations aux amortissements générées.
5. Charges constatées d'avance / factures non parvenues (saisie assistée).
6. Calcul TVA de clôture, cadrage TVA (CA déclaré vs comptabilisé).
7. Calcul du résultat, réintégrations fiscales (amortissements excédentaires VP,
   part LOA non déductible…), IS et écriture 695 le cas échéant.
8. Génération : balance définitive, bilan, compte de résultat, annexes.
9. **Liasse pivot** (2050-suite ou 2033-suite selon régime) remplie case par case
   depuis la balance + retraitements ; règles de cohérence des cases (les contrôles
   du cahier des charges TDFC) exécutées en interne.
10. Verrou de clôture (I4) + à-nouveaux sur l'exercice suivant.

## 6. Renderers (`filings`)

| Sortie | Format | Notes |
|--------|--------|-------|
| FEC | TXT tabulé, art. A.47 A-1 | 18 colonnes normées ; testé contre « Test Compta Demat » en CI. |
| Liasse PDF | PDF fidèle CERFA | Pour relecture/signature humaine. |
| Liasse EDI | EDIFACT/TDFC | Temps 2-3 de la stratégie télédéclaration (doc 02 §5) — produit depuis la liasse pivot. |
| Dépôt comptes annuels | Dossier Guichet Unique INPI | PDF + données structurées. |
| Exports comptables | CSV/XLSX (balance, grand livre, journaux) | Pour l'expert-comptable du client. |
| Déclarations TVA | CA3/CA12 pré-remplies | PDF + pivot (même logique que la liasse). |

## 7. Multi-statuts : matrice de paramétrage (le cœur de la versatilité)

Le statut/régime est une **configuration de premier rang de chaque dossier**, posée
à sa création et modifiable par avenant daté (un changement de régime en cours de
vie est un événement tracé, pas une réécriture). Si un chauffeur est en EURL et le
suivant en SASU, ou si un futur client est en micro, le moteur lit cette matrice —
**jamais de `if statut == "SASU"` éparpillés dans le code.**

**Chaque dossier est strictement indépendant.** Les 200 dossiers du pilote sont
200 configurations posées dossier par dossier : aucun paramètre fiscal n'est
hérité implicitement du tenant. Le tenant peut fournir des **valeurs par défaut de
pré-remplissage** à la création (confort d'onboarding), mais une fois créé, le
dossier porte sa configuration complète en propre — modifier un dossier n'affecte
jamais les autres.

| Paramètre | SASU/EURL à l'IS | SASU/EURL option IR | EI au réel (BIC) | Micro-entreprise | CAE entrepreneur-salarié |
|-----------|------------------|---------------------|------------------|------------------|--------------------------|
| **Disponibilité** | ✅ V1 (majorité du pilote) | ✅ V1 (marginal mais confirmé chez le pilote) | Pack suivant | Pack futur | Pack futur |
| Entité du dossier | La société | La société | L'exploitant | L'exploitant | La coop (1 dossier), sections analytiques |
| Comptabilité | Engagement complète | Engagement complète | Engagement complète | Livre des recettes (+ achats si commerce), suivi de seuils | Portée par la coop |
| Imposition du résultat | IS (2065 + liasse 2050/2033) | IR chez les associés (2031 + annexes 2033/2050) | IR (2031 + annexes) | Micro-BIC/BNC (2042-C-PRO) | N/A (salarié) |
| Dépôt comptes INPI | Oui | Oui | Non | Non | La coop pour elle-même |
| Rémunération dirigeant | 641 (président SASU) / 455+rému gérant | idem selon forme | Prélèvements 108 | N/A | Salaire |
| Usage personnel détecté | 455 CCA | 455 CCA | 108 prélèvements | Signalé (pas d'écriture) | Refacturation interne |
| TVA | Régime TVA configuré par dossier — **réel (simplifié ou normal) opérationnel V1** (les chauffeurs du pilote sont normalement tous au réel), franchise supportée aussi | idem | idem | Franchise par défaut, bascule si seuils | Portée par la coop |

Principes d'implémentation :

- **V1 opérationnelle** = colonnes SASU/EURL IS et option IR, testées de bout en
  bout (golden tests, doc 09 §3). Les autres colonnes sont **présentes dans le
  modèle de données et la configuration dès le jour 1** (on peut créer le dossier,
  saisir le statut), mais leurs règles fiscales et formulaires arrivent par packs
  successifs — sans migration ni refonte, juste des données et des templates en plus.
- Le régime TVA est un axe **orthogonal** au statut (une SASU peut être en
  franchise) : deux paramètres distincts dans la configuration du dossier.
  V1 : réel simplifié et réel normal opérationnels (CA12/CA3) — c'est le cas
  général du pilote — et franchise supportée (pas de TVA sur les écritures,
  surveillance des seuils de bascule).
- **L'option IR est bornée à 5 exercices** (art. 239 bis AB CGI) : le dossier porte
  la date du premier exercice couvert par l'option, le moteur compte les exercices
  restants, **alerte à l'approche du terme** (N-1 et N) et prépare la bascule
  automatique vers la colonne IS à l'exercice suivant la fin de l'option (ou avant,
  en cas de renonciation — avenant daté). La bascule change les formulaires de
  liasse (2031 → 2065+2050) et le traitement du résultat ; elle est traitée comme
  tout changement de régime : événement tracé, jamais rétroactif.
- Chaque colonne de la matrice a son **dossier de référence en golden test** dès
  qu'elle devient opérationnelle — y compris un dossier de référence qui **traverse
  la fin d'option IR** (exercice N en IR, exercice N+1 en IS).

## 8. Ce qu'on ne code PAS en V1 (et qu'on dit clairement)

- Consolidation, groupes, intégration fiscale.
- Multidevise (EUR only).
- Paie/social ; on importe l'OD de paie si le dossier en a.
- Régimes hors SASU/EURL (IS et option IR) : architecture et configuration prêtes
  (§7), règles fiscales et formulaires livrés par packs successifs (EI réel, micro,
  BNC/2035, agricole…) selon la demande client.
