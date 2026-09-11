# 19 — Parcours utilisateur : gestionnaire et chauffeur

> Statut : brouillon à valider — Dernière mise à jour : 2026-09-11.
> Né d'une discussion Louis / Claude Code le 2026-09-06 : décision de
> cadrer et documenter l'accès chauffeur en libre-service **avant** tout
> code, conformément à ce que prévoyait déjà [doc 12 §2.7](12-roadmap-todo.md).
> Ce doc complète [doc 11](11-ux-ui.md) et [doc 14](14-onboarding-offboarding.md)
> — il ne les remplace pas, mais **corrige une hypothèse fausse qu'ils
> partageaient tous les deux jusqu'ici** (§2.1 ci-dessous).
>
> **Révision structurante du 2026-09-11 (Louis)** : nos deux catégories de
> client ne sont pas au même niveau. Le **client interface** — celui qui
> utilise vraiment le produit, dossier par dossier — c'est **l'indiv**
> (le chauffeur/dirigeant). Le **client de gestion globale** — celui avec
> qui on signe un contrat — c'est la **plateforme** (le gestionnaire
> portefeuille). Conséquence directe, qui corrige §2.1 telle qu'écrite au
> 2026-09-06 : la file de revue, l'instruction d'alerte, la clôture et la
> signature **ne sont plus des écrans gestionnaire** — ce sont des écrans
> indiv, parce que c'est l'indiv qui a dépensé, qui sait, et dont c'est la
> donnée. Le gestionnaire garde un état des lieux agrégé et l'onboarding,
> rien de plus (§6 refaite). Recoupe doc 02 §2.3 (« l'utilisateur
> professionnel valide ») : c'est l'indiv, cet utilisateur professionnel,
> pas le gestionnaire.

## 1. Pourquoi ce doc

Jusqu'ici, le chauffeur n'existait dans la doc qu'à travers **un seul
écran** : la page de signature (doc 11 §3.3), zéro compte, lien + OTP. Ce
n'est plus le cas. Le chauffeur doit maintenant avoir **son propre compte**,
relié à ses propres écritures bancaires, avec une vraie application — pas
un lien ponctuel. Ce doc décrit ce parcours, celui du gestionnaire tel qu'il
évolue en conséquence, et sert directement de base au nouveau [doc 17](17-plan-demo-backend.md)
(plan de démo).

## 2. Un compte, deux liens — pas deux systèmes

> **Précisé le 2026-09-11 (doc 03 §7)** : « gestionnaire » et « indiv » ne
> sont pas deux types de compte différents, deux systèmes d'auth à
> construire séparément. **Un compte peut porter un lien `dossier_id`**
> (accès indiv à ce dossier, §2.2) **et/ou un lien `tenant_id`** (accès
> gestionnaire à ce portefeuille, §2.1) — les deux indépendamment, les
> deux à la fois possible sur le même compte (§2.3, le mono). Ce qui suit
> décrit ce que chaque lien donne comme accès, pas deux produits
> distincts.

### 2.1 Le gestionnaire (PC / web) — **corrigé le 2026-09-11** : état des lieux, pas cockpit détaillé

**Ce que ce doc disait avant (2026-09-06) était faux sur un point
important** : « rien ne change sur l'interface portefeuille, file de
revue et clôture incluses ». En fait si — la file de revue (doc 11 §3.1),
l'instruction d'alerte (doc 11 §3.2), la clôture (doc 06 §5) et la
signature (doc 11 §3.3, doc 20) **deviennent des écrans indiv**, pas
gestionnaire (§2.4 explique pourquoi). Ce qui reste vraiment côté
gestionnaire :

- Dashboard portefeuille : **agrégats seulement** (CA/charges/résultat par
  dossier, nombre de dossiers actifs, régime TVA/statut) — pas le détail
  d'une transaction, jamais.
- **Visibilité de premier rang sur l'onboarding** de ses indivs : qui a un
  compte actif, qui a été invité et n'a pas répondu, qui n'a toujours pas
  de compte (§3.2, inchangé).
- Invitation, individuelle ou en masse (§3.1, étendu le 2026-09-11).
- **Peut-être** un indicateur « documents de clôture déposés : oui/non »
  par dossier — **désactivé par défaut, en attente de confirmation
  juridique** (§2.4, doc 02 §10).

### 2.2 Le chauffeur (mobile) — nouveau

Le chauffeur a son propre compte, sa propre app (webapp responsive pour la
démo, cible finale = app native App Store / Play Store). Ce compte lui sert
à :

- Voir ses propres transactions bancaires et leur catégorisation.
- Prendre en photo ses tickets/justificatifs au fil de l'eau.
- Répondre à de petites questions de catégorisation quand le système hésite.
- Optionnellement connecter lui-même sa banque (§4).
- Signer ses documents (l'écran qui existait déjà, doc 11 §3.3 — il devient
  une étape parmi d'autres, pas le seul écran).

### 2.3 Mode mono-compte — **résolu le 2026-09-11**, ce n'est même plus un « mode »

**La tension notée dans une version précédente de ce doc est résolue.**
Un indépendant qui gère sa propre compta seul n'a pas de statut spécial :
c'est un compte dont le lien `tenant_id` (gestionnaire) et le lien
`dossier_id` (indiv) **pointent vers le même portefeuille d'un seul
dossier — le sien** (doc 03 §7). Aucun branchement particulier à coder :
- Il a accès à l'écran gestionnaire (§2.1) — état des lieux agrégé —
  **qui n'affiche qu'un seul dossier**, le sien. Techniquement inutile
  (pas grand-chose à agréger sur un portefeuille de un), mais pas un
  écran en moins ni un cas à exclure.
- Il a accès à l'écran indiv (§2.2) — son propre dossier en détail,
  transactions, revue, clôture, signature.

Les **deux** interfaces (web et mobile/webapp) restent celles déjà
décrites §7 — rien de spécifique au mono à construire là non plus,
c'est la même personne qui navigue entre les deux, pas un habillage à
part.

### 2.4 Ce que le gestionnaire ne voit jamais (et ce qui reste à confirmer légalement)

Le gestionnaire n'a **aucun accès** aux transactions, justificatifs,
détail des écritures ou documents d'un dossier — c'est la donnée de
l'indiv, générée par ses propres dépenses, pas celle du gestionnaire.
Même le fait de savoir si une pièce a été signée ou déposée est **une
donnée dérivée de la comptabilité d'un tiers**, pas un simple statut
technique anodin — Louis n'est pas certain que même *ça* soit conforme
RGPD/monopole d'expertise comptable (doc 02 §2, doc 02 §10). Tant que ce
n'est pas confirmé par un juriste : **le gestionnaire ne voit rien de
dossier-spécifique au-delà des agrégats de §2.1** — pas d'option cachée
activée par défaut en attendant.

## 3. Modèle de compte et onboarding

### 3.1 Qui crée quoi

**Pas de self-signup public.** Le tenant (le gestionnaire) est toujours créé
par AxeL — ça ne change pas par rapport à doc 14 §1.3. Ce qui est nouveau :
chaque chauffeur doit ensuite avoir **son propre compte utilisable**, pas
juste une ligne en base créée par CSV (doc 14 §1.2/1.4). Deux façons d'y
arriver, non exclusives :

- **Le gestionnaire invite lui-même ses chauffeurs** depuis son interface
  (self-service à ce niveau-là, pas au niveau tenant) — soit **au lien
  individuel** (un email à la fois, déjà construit), soit **en masse
  depuis une base clients** (nouveau, précisé 2026-09-11 : import d'une
  liste — CSV a minima — qui déclenche une invitation par ligne, avec
  rapport d'envoi succès/erreur par ligne, même logique que l'import de
  dossiers doc 14 §1.4 mais pour des invitations, pas des configurations
  comptables). **Distinct** du CSV dossiers (doc 14 §1.4) : celui-ci crée
  des comptes utilisables, l'autre configure des dossiers — un gestionnaire
  peut avoir besoin des deux, dans n'importe quel ordre.
- **AxeL peut assister** le gestionnaire pour cette étape s'il en a besoin
  (mêmes principes que l'aide à l'onboarding déjà prévue doc 14).

Le CSV en masse (doc 14 §1.4) continue d'exister pour créer les *dossiers*
(configuration comptable) ; l'invitation chauffeur est une étape
supplémentaire et distincte qui donne accès à *un compte utilisable*, pas
seulement à une fiche.

### 3.2 Visibilité gestionnaire sur l'onboarding des chauffeurs

Extension directe du pattern déjà existant pour les consentements bancaires
(doc 14 §2.2, « écran de premier rang, pas caché dans les paramètres ») —
plutôt que d'inventer un nouveau concept, le même panneau affiche aussi le
statut d'invitation par chauffeur :

| Statut | Sens |
|---|---|
| `non_invité` | Dossier créé, aucune invitation envoyée |
| `invité` | Invitation envoyée, en attente de réponse |
| `compte_créé` | Le chauffeur a créé son compte mais pas terminé son propre onboarding (§5) |
| `actif` | Compte utilisé normalement |
| `inactif` | Compte créé mais plus utilisé depuis N jours (seuil à définir) |

### 3.3 Option avancée : synchronisation API — prévue, pas construite pour la démo

Certains gestionnaires ont leur propre base de données de chauffeurs.
Fonctionnalité prévue : une connexion API vers cette base, avec détection
des nouveaux chauffeurs et, **en option explicite (opt-in, désactivée par
défaut)**, envoi automatique d'une invitation dès qu'un nouveau chauffeur
apparaît côté gestionnaire. Ce n'est **jamais** un comportement par défaut —
le gestionnaire doit l'activer consciemment dans ses réglages.

Cadré ici pour ne pas avoir à le repenser plus tard, mais **hors scope de
la démo** (doc 17) — c'est un vrai chantier d'intégration (auth API tierce,
mapping de champs, sécurité) qui n'apporte rien à la validation du parcours
et des calculs.

## 4. Connexion bancaire : deux modes, par dossier

Le principe déjà acté « statut/régime = configuration de premier rang par
dossier » (doc 06 §7, doc 03 §3bis) s'étend à l'accès bancaire. Un nouveau
champ de configuration, au même niveau que `regime_imposition` ou
`tva_recettes_regime` (doc 14 §1.2) :

| `mode_acces_bancaire` | Qui connecte | Cas d'usage |
|---|---|---|
| `gestionnaire` | Le gestionnaire, via Digifactory (doc 16) | Cas pilote actuel — l'indiv n'a rien à connecter : soit les transactions arrivent directement dans son app (déjà remontées côté Digifactory), soit un écran « ça arrive bientôt » tant qu'elles n'y sont pas encore — jamais de bouton Bridge affiché dans ce mode. |
| `chauffeur_direct` | L'indiv lui-même, depuis son app, **via Bridge en direct** (précisé 2026-09-11, doc 16 §8) | Indiv autonome sans agrégateur côté gestionnaire — le bouton de connexion bancaire dans l'app **est** Bridge Connect, pas un choix parmi d'autres. |

Les deux passent par la même interface `DataProvider` (doc 13 §2) — aucun
changement dans le moteur selon le mode retenu, seule la configuration du
dossier change. **`chauffeur_direct` reste bloqué techniquement** tant que
`BridgeProvider` (doc 16 §8, doc 12 §1.2) n'est pas construit — c'est un
vrai prérequis, pas du réagencement d'écran ; le bouton actuel (doc 17 §9)
est un stub visuel volontaire en attendant. Le dashboard de consentements
(doc 14 §2.2) s'étend pour couvrir les deux : quand c'est l'indiv qui
connecte lui-même, c'est lui qui reçoit les relances d'expiration de
consentement (et non le gestionnaire) — cohérent avec le mode de relance
déjà configurable par dossier.

**Pour la démo (doc 17)** : les deux modes sont visibles à l'écran (le
réglage existe, l'UI existe). Le mode `gestionnaire` (Digifactory) est
câblé en priorité — c'est le cas réel du pilote. Le mode `chauffeur_direct`
est un objectif « si le temps le permet » (§6), pas un bloquant — Louis
relance Digifactory sur le token (doc 16 §7) pour que ce chemin fonctionne
réellement avant la fin du mois.

## 5. Parcours détaillé — l'indiv (mobile/webapp) — **réécrit le 2026-09-11**

**Ce parcours porte maintenant tout ce qui touche à ses propres données** :
transactions, revue, justificatifs, clôture, signature. Rien de tout ça
n'existe plus côté gestionnaire (§2.1, §2.4).

### 5.1 Onboarding

1. **Réception de l'invitation** (email/SMS) envoyée par le gestionnaire ou AxeL.
2. **Création de compte** — email + mot de passe (ou lien magique), pas de
   self-signup libre, mais un vrai compte personnel. **Option de changer
   son mot de passe** (précisé 2026-09-11) — pour la confidentialité, le
   mot de passe initial (lien d'invitation) ne doit pas rester le seul.
3. **Complément de profil** si nécessaire (une partie est déjà pré-remplie
   depuis la fiche dossier créée côté gestionnaire).
4. **Connexion bancaire** — trois cas concrets selon `mode_acces_bancaire`
   (§4, précisé 2026-09-11) :
   - `chauffeur_direct` : il relie sa banque **via Bridge**, dans l'app.
   - `gestionnaire`, transactions déjà remontées : il les voit directement,
     rien à connecter.
   - `gestionnaire`, rien encore remonté : écran d'attente explicite
     (« vos transactions arrivent bientôt »), pas un vide silencieux.

### 5.2 Traitement au fil de l'eau — pas une revue de fin d'année

**Principe central, précisé 2026-09-11** : dès qu'une transaction arrive et
que le pipeline (règles/ML/LLM) ne sait pas trancher, l'indiv reçoit une
**notification** pour la traiter au plus vite — pas une pile qui s'accumule
jusqu'à la clôture. Bénéfice double : plus simple pour l'indiv (petit flux
continu, pas une session marathon en fin d'exercice), et ça répartit la
charge de notre côté (support, LLM, instruction) sur l'année plutôt que de
tout concentrer sur la période de clôture — risque déjà identifié doc 09
§7 (charge, clôtures groupées).

5. **Vue de ses transactions** : ce qui a été catégorisé, ce qui reste à
   trancher — version simplifiée, langage clair, pas le vocabulaire
   comptable pro.
6. **Notification + petite question de catégorisation** quand le système
   hésite (« repas ou autre ? », « personnelle ou pro ? ») — dès que la
   transaction arrive, pas en lot différé. Même logique que l'ancienne
   « file de revue » (doc 11 §3.1) — **cet écran est maintenant ici, plus
   côté gestionnaire** (§2.1).
7. **Photo de justificatif** au fil de l'eau, associée automatiquement à la
   transaction correspondante quand c'est possible.

**Système de notification : entièrement à construire, rien n'existe
aujourd'hui** (pas d'email transactionnel, pas de notif in-app/push) — un
vrai chantier technique, pas une case UI à ajouter (à chiffrer, doc 12).

### 5.3 Clôture — la boucle de complétude bancaire

8. **Demande de clôture** en fin d'exercice : l'indiv confirme que la
   dernière écriture connue correspond bien à sa vraie banque (doc 06 §5bis
   — c'est cette confirmation, pas une date, qui fait foi). Tant que ce
   n'est pas confirmé, chaque nouvelle synchro Bridge/Digifactory qui
   remonte de nouvelles écritures redemande cette confirmation.
9. Une fois confirmé (et comme le traitement s'est fait au fil de l'eau,
   §5.2 — pas de gros arriéré à traiter d'un coup) : génération des
   documents (greffe, INPI, TVA, liasse — doc 06 §6, doc 20).
10. **Première signature — la validation** (notification dédiée) : l'indiv
    atteste être d'accord avec les comptes tels que produits. **Cette
    signature nous protège** (doc 02 §2.3 : « l'utilisateur professionnel
    valide ») — elle n'a pas besoin d'être qualifiée RGS, ce n'est pas la
    même chose que la signature légale de dépôt (doc 20 §4bis).
11. **Envoi** vers les organismes concernés (impôts, greffe, INPI, TVA…).
12. **Seconde signature — la légale** : certains organismes renvoient des
    documents à signer après coup (ex. le document de synthèse INPI,
    doc 20 §4) — c'est là qu'intervient la vraie signature qualifiée RGS,
    par indiv, jamais par AxeLCompta (doc 20 §6, tranché 2026-09-11).

## 6. Parcours détaillé — le gestionnaire (PC / web) — **réécrit le 2026-09-11**

**Beaucoup plus court qu'avant** : plus de file de revue, plus de clôture,
plus de signature — tout ça a migré côté indiv (§5). Ce qui reste :

1. Réception du tenant configuré par AxeL (doc 14 §1.3) — AxeL signe avec
   le gestionnaire (contrat B2B), pas avec chaque dossier individuellement.
2. Import en masse des dossiers (CSV, doc 14 §1.4) — configuration
   comptable de chaque indiv.
3. **Invitation des indivs** — lien individuel ou **import en masse depuis
   une base clients** (§3.1, précisé 2026-09-11) — et suivi de leur statut
   d'onboarding (§3.2), écran de premier rang, comme le dashboard
   consentements.
4. **Dashboard portefeuille — état des lieux agrégé seulement** (§2.1) :
   CA/charges/résultat par dossier, statut d'onboarding, éventuellement
   « documents déposés » si la confirmation juridique arrive (§2.4). Jamais
   le détail d'une transaction, d'un justificatif ou d'une signature.

## 7. Portée technique

- **Démo** : webapp responsive pour le rôle chauffeur (ouverte depuis un
  téléphone, pas d'installation), webapp desktop classique pour le rôle
  gestionnaire — même socle front, deux habillages, cohérent avec le
  principe déjà acté doc 11 §1bis (mono = portefeuille sans la couche
  portefeuille — même logique appliquée ici entre gestionnaire et
  chauffeur : composants partagés, habillage différent).
- **Cible finale** (post-démo) : app native chauffeur sur App Store / Play
  Store. Le gestionnaire reste PC/web — aucune ambition mobile de ce côté.

## 8. Ce qui reste ouvert (non traité ici)

- Design précis des écrans mobiles (DESIGN.md n'a aujourd'hui de règles
  mobiles que pour la page de signature, doc DESIGN.md « Comportement
  responsive ») — à faire une fois ce parcours validé, avant le code.
- Détail technique de l'option de synchronisation API (§3.3) — volontairement
  laissé pour plus tard.
- Seuil d'inactivité pour le statut `inactif` (§3.2) — à définir avec Louis
  à l'usage, pas bloquant pour la démo.

**Ajoutés le 2026-09-11, chantiers réels pas encore scopés** :

- **Système de notification** (§5.2) — canal (email transactionnel ? push ?
  in-app seulement ?), déclencheurs, fréquence. Rien n'existe.
- **Import en masse des invitations** (§3.1, §6) — parsing, validation,
  rapport d'erreurs, format accepté (CSV a minima) ; distinct du CSV
  dossiers déjà spécifié doc 14 §1.4.
- **Boucle de clôture/complétude bancaire** (§5.3, doc 06 §5bis) — durée du
  délai de battement et politique CCA/FNP précise à valider avec un
  expert-comptable ; mécanique de redemande de confirmation à chaque
  nouvelle écriture pas encore détaillée techniquement.
- **`BridgeProvider` direct** (§4, doc 16 §8, doc 12 §1.2) — prérequis
  technique du mode `chauffeur_direct`, pas commencé.
- **Confirmation juridique sur la visibilité gestionnaire** (§2.4, doc 02
  §10) — bloquant pour savoir si même « documents déposés : oui/non » est
  affichable au gestionnaire.
- **Rework de ce qui a été construit le 2026-09-11 avant cette révision**
  (doc 17 §9 Semaine 4, greffe/INPI) : `ClotureSection.tsx` et
  `GreffeInpiSection.tsx` sont aujourd'hui sur la fiche dossier
  **gestionnaire** — à déplacer côté indiv une fois qu'on code ce parcours.
  Pas fait dans cette révision de doc (Louis : « on fera du code plus
  tard ») — noté pour ne pas l'oublier.
