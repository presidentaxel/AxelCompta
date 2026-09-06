# 19 — Parcours utilisateur : gestionnaire et chauffeur

> Statut : brouillon à valider — Dernière mise à jour : 2026-09-06.
> Né d'une discussion Louis / Claude Code le 2026-09-06 : décision de
> cadrer et documenter l'accès chauffeur en libre-service **avant** tout
> code, conformément à ce que prévoyait déjà [doc 12 §2.7](12-roadmap-todo.md).
> Ce doc complète [doc 11](11-ux-ui.md) (reste la référence pour l'interface
> gestionnaire PC) et [doc 14](14-onboarding-offboarding.md) (reste la
> référence pour l'onboarding du tenant côté AxeL) — il ne les remplace pas.

## 1. Pourquoi ce doc

Jusqu'ici, le chauffeur n'existait dans la doc qu'à travers **un seul
écran** : la page de signature (doc 11 §3.3), zéro compte, lien + OTP. Ce
n'est plus le cas. Le chauffeur doit maintenant avoir **son propre compte**,
relié à ses propres écritures bancaires, avec une vraie application — pas
un lien ponctuel. Ce doc décrit ce parcours, celui du gestionnaire tel qu'il
évolue en conséquence, et sert directement de base au nouveau [doc 17](17-plan-demo-backend.md)
(plan de démo).

## 2. Les deux comptes

### 2.1 Le gestionnaire (PC / web) — inchangé dans son principe, doc 11 reste la référence

Rien ne change sur l'interface portefeuille elle-même (dashboard, fiche
dossier, file de revue, clôture — doc 11 §2-3). Ce qui s'ajoute : le
gestionnaire doit avoir une **visibilité de premier rang** sur l'état
d'onboarding de ses chauffeurs — il ne doit jamais être « dans le noir » sur
qui a un compte actif, qui a été invité et n'a pas encore répondu, qui n'a
toujours pas de compte (§3.2).

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

### 2.3 Mode mono-compte — même logique, pas une troisième UI

Un indépendant qui gère sa propre compta seul (sans gestionnaire) suit
**le même principe d'axe déjà acté en doc 11 §1bis** : le mode mono est le
mode portefeuille sans la couche portefeuille, sur les mêmes écrans PC/web.
Le mobile, pour lui aussi, sert **uniquement au confort du quotidien**
(capture de ticket, question rapide) — **pas** à piloter l'ensemble de sa
compta. La gestion réelle (clôture, liasse, suivi) reste sur l'interface
web, qu'il y ait un portefeuille de 200 dossiers ou un seul.

En clair : il n'y a que **deux UI**, pas trois — web (gestionnaire ou mono)
et mobile (chauffeur ou usage quotidien du mono) — et le mobile n'a jamais
vocation à tout gérer.

## 3. Modèle de compte et onboarding

### 3.1 Qui crée quoi

**Pas de self-signup public.** Le tenant (le gestionnaire) est toujours créé
par AxeL — ça ne change pas par rapport à doc 14 §1.3. Ce qui est nouveau :
chaque chauffeur doit ensuite avoir **son propre compte utilisable**, pas
juste une ligne en base créée par CSV (doc 14 §1.2/1.4). Deux façons d'y
arriver, non exclusives :

- **Le gestionnaire invite lui-même ses chauffeurs** depuis son interface
  (self-service à ce niveau-là, pas au niveau tenant).
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
| `gestionnaire` | Le gestionnaire, via Digifactory (doc 16) | Cas pilote actuel — le chauffeur n'a rien à faire |
| `chauffeur_direct` | Le chauffeur lui-même, depuis son app | Chauffeur autonome, ou gestionnaire qui préfère déléguer |

Les deux passent par la même interface `DataProvider` (doc 13 §2) — aucun
changement dans le moteur selon le mode retenu, seule la configuration du
dossier change. Le dashboard de consentements (doc 14 §2.2) s'étend pour
couvrir les deux : quand c'est le chauffeur qui connecte lui-même, c'est lui
qui reçoit les relances d'expiration de consentement (et non le
gestionnaire) — cohérent avec le mode de relance déjà configurable par
dossier.

**Pour la démo (doc 17)** : les deux modes sont visibles à l'écran (le
réglage existe, l'UI existe). Le mode `gestionnaire` (Digifactory) est
câblé en priorité — c'est le cas réel du pilote. Le mode `chauffeur_direct`
est un objectif « si le temps le permet » (§6), pas un bloquant — Louis
relance Digifactory sur le token (doc 16 §7) pour que ce chemin fonctionne
réellement avant la fin du mois.

## 5. Parcours détaillé — le chauffeur (mobile)

1. **Réception de l'invitation** (email/SMS) envoyée par le gestionnaire ou AxeL.
2. **Création de compte** — email + mot de passe (ou lien magique), pas de
   self-signup libre, mais un vrai compte personnel.
3. **Complément de profil** si nécessaire (une partie est déjà pré-remplie
   depuis la fiche dossier créée côté gestionnaire).
4. **Connexion bancaire** — soit rien à faire (`mode_acces_bancaire:
   gestionnaire`), soit connexion directe (`chauffeur_direct`, §4).
5. **Vue de ses transactions** : ce qui a été catégorisé, ce qui reste à
   trancher — version simplifiée, langage clair, pas le vocabulaire
   comptable pro de la file de revue gestionnaire.
6. **Petites questions de catégorisation** quand le système hésite
   (« repas ou autre ? ») — la même logique que la file de revue (doc 11
   §3.1) mais présentée simplement.
7. **Photo de justificatif** au fil de l'eau, associée automatiquement à la
   transaction correspondante quand c'est possible.
8. **Signature des documents** le moment venu (doc 11 §3.3, inchangé dans
   son fonctionnement, intégré comme une étape du parcours plutôt que le
   point d'entrée unique).

## 6. Parcours détaillé — le gestionnaire (PC / web)

Rappel de ce qui existe déjà (doc 11, inchangé) + un écran qui s'ajoute :

1. Réception du tenant configuré par AxeL (doc 14 §1.3).
2. Import en masse des dossiers (CSV, doc 14 §1.4) — configuration
   comptable de chaque chauffeur.
3. **Nouveau** : invitation des chauffeurs (un par un ou en masse) et suivi
   de leur statut d'onboarding (§3.2) — écran de premier rang, comme le
   dashboard consentements.
4. Dashboard portefeuille, file de revue, clôture, liasse, envoi pour
   signature — inchangé (doc 11 §2-3).

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
