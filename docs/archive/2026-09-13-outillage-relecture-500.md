# 2026-09-13 — Outillage de la relecture des 500 lignes

> Session Claude Code du 2026-09-13 (soir), pour reprendre facilement demain.
> Concerne doc 12 §0.2 (item "500 lignes relues à la main") et §0.3 (écart ML
> 79,5%/94,4%). Contexte complet : [[axelcompta-project]] / mémoire Claude.

## État au moment d'écrire cette note

**7/500 lignes traitées manuellement** dans
`_AUDIT_DONNEES/resultats/echantillon_500_a_relire.csv` (0 via la pré-passe
auto — elle a été ajoutée après le début de la vraie relecture, tu ne l'as
pas encore lancée). Sauvegarde propre du fichier à 0/500 disponible :
`echantillon_500_a_relire.csv.bak-20260913-183515`.

## Ce qui a été construit : `relecture_rapide.py`

Script dans `_AUDIT_DONNEES/resultats/`, aucune dépendance externe.

```bash
cd _AUDIT_DONNEES/resultats
python3 relecture_rapide.py
```

**Commandes pendant la relecture** : `Entrée` accepte `categorie_proposee`,
un numéro corrige (menu affiché au lancement, `?` pour le revoir), `i`
accepte mais tague "pas de justificatif, jugé sur le libellé seul", `s`
saute (revue plus tard), `q` sauvegarde et quitte (reprise exacte).

Écriture atomique après **chaque** décision — aucune perte possible sur un
Ctrl-C.

## La pré-passe automatique (pas encore lancée sur le vrai fichier)

Au lancement, le script propose de valider d'un coup les lignes qui ne
présentent **aucun** signal de risque identifié : catégorie non-ambiguë,
transaction simple (pas composite), libellé sans propositions
contradictoires selon les occurrences, pas d'enseigne connue pour poser
un doute réel. Sur l'échantillon actuel, ça représente **~300-307 lignes
sur 500** — il ne resterait qu'**environ 200 lignes à vraiment regarder**.
Les lignes auto-validées sont taguées `✅ validé automatiquement — non
revu ligne à ligne`, distinctes de tes vraies décisions.

**Demain, au premier lancement, dis "Entrée" (oui) à la question de la
pré-passe** — c'est le plus gros gain de temps restant.

## Regroupement des libellés répétés

Un libellé identique (Uber, Qonto, Total, Sanef, Toyota, Heetch,
PayPal...) ne se juge qu'une fois : le script propose ensuite de
l'appliquer à toutes les autres occurrences. Deux exceptions, jamais
regroupées : le libellé générique `FOURNISSEUR DIVERS - Multiples
Comptes ou Produits` (35 occurrences, recouvre des opérations
différentes à chaque fois), et tout libellé où le compte PCG proposé
diffère d'une occurrence à l'autre (21 groupes identifiés) — appliquer la
même décision à tout le groupe serait faux dans ces cas.

## Aides affichées sur chaque ligne

- **Dossier réel + chemin du fichier FEC source**, retrouvés via
  `sortie/mapping_dossiers_NE_PAS_COMMIT.csv` (jamais committé). Le disque
  externe (`/run/media/louitos/Louitos/.../Dossier Chauffeurs`) **n'est pas
  monté sur cette machine** — les chemins affichés ne s'ouvriront pas tant
  qu'il n'est pas branché.
- **Référence de pièce comptable** (`piece_ref`, ex. `PAI-053`), retrouvée
  pour 480/500 lignes via `fec_ml_taxonomie.csv` (20 ambiguës, affichées
  toutes plutôt que de deviner) — à chercher dans le dossier FEC ci-dessus
  une fois le disque branché.
- **`✓ dossier clos/repris par le comptable`** quand le chemin contient
  "Clôture", "Reprise dossier" ou "fin contrat" (197/500 lignes) — signal
  positif, l'écriture vient d'un exercice bouclé, pas d'un brouillon.
- **`⚠ catégorie à vraiment vérifier`** sur les ~40 lignes dans
  `repas_et_receptions` / `a_verifier_location_materiel` /
  `non_categorise_a_verifier` — les 3 catégories que `taxonomie.md`
  flague elle-même comme jamais tranchées finement, même côté comptable.
- **`⚠ transaction composite`** sur les 136 lignes à double jambe (doc 06
  §3bis) — à vérifier que la décomposition recette/commission tient.
- **`🔍` glossaire** : recherche web faite le 2026-09-13 sur 7 enseignes
  peu claires (voir tableau ci-dessous). Ne couvre que ces 7 sur ~276
  enseignes non-évidentes au total — le reste (noms de personnes,
  libellés tronqués) n'a pas de piste supplémentaire, ça reste un
  jugement sur le libellé.

## Deux vraies erreurs de catégorisation trouvées (🚩 à vérifier en priorité)

| Enseigne | Ce qu'elle est réellement | Catégorie proposée actuelle | Probablement correct |
|---|---|---|---|
| **SPB Assurance Mobile** | Courtier en assurance affinitaire pour téléphones/smartphones (resilier.fr, afub.org) | `assurance_vehicule` | Faux — ce n'est pas une assurance véhicule |
| **VIAXEL** | Filiale Crédit Agricole Consumer Finance, financement de véhicules/LOA (transfertleasing.fr) | `a_verifier_location_materiel` | Probablement `loa_credit_bail_vehicule` |
| **FLEXI-FLEET** | Loueur de véhicules VTC, Compiègne (flexifleet.fr) | `a_verifier_location_materiel` | Probablement `loa_credit_bail_vehicule` |

Ces 3 sont exclues de la pré-passe automatique (flag 🚩), donc tu les
verras forcément en revue manuelle.

## Un vrai incident pendant la construction de l'outil, corrigé

En testant le script, j'ai accidentellement laissé 2 lignes réelles se
remplir dans le vrai fichier (au lieu de rester dans mes copies de test).
Détecté par relecture, restauré depuis la sauvegarde faite en tout début
de session, confirmé identique par hash MD5. Cause exacte non
reproduite malgré une tentative ciblée — je vérifie maintenant le hash du
fichier réel avant/après chaque test pour ne pas que ça se reproduise
silencieusement.

## Point important à ne pas perdre de vue : ce script ne résout PAS encore l'écart 79,5%/94,4% du doc 12

Le récapitulatif du script donne ton taux d'accord avec `categorie_proposee`
(qui vient du compte PCG assigné par le comptable réel, pas d'un modèle
ML). C'est un indicateur utile, mais **ce n'est pas** la mesure de
précision ML attendue par le doc 12/ADR-007. Cette dernière demande de
comparer `categorie_validee` (une fois les 500 lignes complétées) aux
prédictions du modèle **entraîné sur le seul libellé bancaire**
(`entrainer_modele_baseline.py`, celui du spike ADR-007) — une étape
séparée, pas encore faite. À prévoir une fois la relecture terminée.

## Pour demain, dans l'ordre

1. `cd _AUDIT_DONNEES/resultats && python3 relecture_rapide.py`
2. Accepter la pré-passe automatique proposée au lancement (`Entrée`).
3. Traiter les ~200 lignes restantes — prêter une attention particulière
   aux 3 lignes 🚩 (SPB, VIAXEL, FLEXI-FLEET) et aux ~40 lignes ⚠
   catégorie ambiguë.
4. Si tu veux vérifier une pièce comptable/le fichier FEC source :
   brancher le disque externe (`Dossier Chauffeurs`) avant de lancer le
   script, sinon les chemins affichés resteront juste informatifs.
5. Une fois à 500/500 : redemander la mise à jour de doc 12 (case cochée)
   et lancer l'étape séparée décrite ci-dessus (comparer au modèle
   ML entraîné sur le libellé seul) pour trancher réellement l'écart
   79,5%/94,4%.
