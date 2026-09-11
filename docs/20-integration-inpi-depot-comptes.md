# 20 — Dépôt des comptes annuels (Guichet Unique INPI)

> **Statut : spike fait le 2026-09-11** (doc 17 §9 Semaine 4, doc 17 §10 —
> risque « schéma du dossier greffe/INPI inconnu »). Contrairement à
> Digifactory (doc 16) avant le doc 16, le schéma **est** documenté
> publiquement par l'INPI — pas besoin d'attendre un contact fournisseur
> pour commencer à coder. Le vrai blocage trouvé n'est pas technique, voir
> §5.
> Dernière mise à jour : 2026-09-11.

## 1. Contexte et décision

Doc 02 §6 : « Depuis 2023, formalités via le Guichet Unique (INPI). […]
Phase 1 : génération du dossier complet prêt à déposer (PDF + données),
dépôt manuel par le client. Phase 2 : intégration API. » Ce spike vérifie
si cette hypothèse (API = phase 2 seulement) tient — **elle ne tient
qu'à moitié** : l'API de dépôt existe et est documentée dès aujourd'hui,
mais un vrai blocage réglementaire (§5) rend la génération du dossier
« prêt à déposer manuellement » toujours la bonne cible court terme,
pour une raison différente de celle supposée au départ (pas un manque
d'accès API, mais une signature électronique qualifiée qu'AxeLCompta ne
peut pas fournir seul).

**Sources** (téléchargées le 2026-09-11 depuis
[inpi.fr/ressources/formalites-dentreprises/acces-aux-api-guichet-unique](https://www.inpi.fr/ressources/formalites-dentreprises/acces-aux-api-guichet-unique),
accès libre, pas de compte requis pour lire la doc) :
- **Contrat d'interface** (juin 2026, PDF, 52 pages) — le document
  principal de ce spike, contrat des endpoints REST.
- **Dictionnaire de données** (juin 2026, xlsx) — détail champ par champ,
  **pas encore dépouillé** (le contrat suffit pour l'estimation, pas pour
  une implémentation complète).
- **Catégorisation des activités** / **Liste des formes juridiques** —
  référentiels annexes, pas regardés (pas nécessaires pour le dépôt de
  comptes en tant que tel).

Une doc technique séparée existe pour la **consultation** des comptes
annuels d'un tiers (`documentation technique API_comptes_annuels v5.pdf`,
API Entreprise/RNE) — **non pertinente ici** : c'est une API de lecture
(chercher les comptes déjà déposés d'une entreprise), pas de dépôt.
À ne pas confondre si un futur spike y retombe.

## 2. Accès

Authentification requise (compte sur `procedures.inpi.fr`), **pas testée
en réel dans ce spike** — contrairement à Digifactory (doc 16), aucun
identifiant n'a été demandé/reçu à ce jour, ce spike s'est fait entièrement
sur la doc publique. Base URL de référence dans le contrat :
`guichet-unique.inpi.fr` (`https://guichet-unique.inpi.fr/api/docs/mandataire`
pour la doc Swagger interactive, non consultée ici faute de compte).

## 3. Le service de dépôt des comptes annuels

```
POST /api/annual_accounts
```

Corps (extrait du contrat, §4.1) :

```json
{
  "content": {
    "personnePhysique": {"...": "identité du déclarant, si personne physique"},
    "personneMorale": {"...": "identité de la société déposante"},
    "declarant": {"...": "qui dépose, au nom de qui"},
    "comptesAnnuels": {
      "comptesConsolides": null,
      "dateCloture": null,
      "dateDebutExerciceComptable": null,
      "dateFinExerciceComptable": null,
      "dispenseDepotAnnexes": null,
      "depotSimplifie": null,
      "modeExpert": {},
      "compteBilan": { "pagination": {}, "confidentiel": null },
      "compteResultat": { "pagination": {}, "confidentiel": null }
    }
  },
  "typePersonne": "P"
}
```

**Lecture (non confirmée dans le dictionnaire de données, ⚠️ à vérifier
avant implémentation)** : `compteBilan`/`compteResultat` ne portent pas de
montants case par case (pas un CERFA 2065 ré-implémenté) — `pagination`
suggère qu'ils pointent vers des **pages d'un PDF joint en pièce jointe**
(le bilan et le compte de résultat sont des sections d'un même document
PDF déposé, comme le fait déjà `PdfLiasseSimplifieeRenderer`/
`PdfCerfa2065Renderer`, doc 18). `confidentiel` correspond probablement à
l'option légale de confidentialité du compte de résultat pour les petites
entreprises (C. com. art. L.232-25) — cohérent avec le modèle de données
déjà pensé pour la matrice statut/régime (doc 06 §7), mais **à confirmer
avec le dictionnaire de données**, pas supposé ici.

**Pièces jointes** (§3.3 du contrat, mécanisme générique réutilisé ici) :
base64 dans `documentBase64`, format PDF uniquement, **10 Mo max par
pièce**, avec métadonnées (`nomDocument`, `typeDocument`, `path` —
l'endroit du JSON où la pièce s'attache). Codes retour standards (201
créé, 400 erreur de saisie, 401/403 auth, 500 serveur).

Endpoints complémentaires, non détaillés ici (contrat §4.2-4.7) : lister
les dépôts (`GET /api/annual_accounts`, filtrable par statut —
`VALIDATION_PENDING`, `SIGNATURE_PENDING`, `PAYMENT_PENDING`,
`AMENDMENT_*`, `VALIDATED`, `REJECTED`), détail d'un dépôt, version
allégée, régularisation, suppression d'un dépôt non payé, transfert à un
autre utilisateur.

## 4. Signature — le vrai chemin critique

**Différent de tout ce que le projet a signé jusqu'ici (doc 17 §8 :
« signature mockée, vrai faux » pour le chauffeur).** Le dépôt de comptes
annuels au greffe est soumis à l'art. R.123-5 du code de commerce :
signature électronique **avancée**, reposant sur un **certificat
qualifié** au sens du règlement eIDAS (UE 910/2014). Ce n'est pas une case
à cocher côté produit, c'est une obligation légale du dépôt lui-même.

Circuit documenté (contrat §6.3) :
1. `POST /api/annual_accounts` (les données + le PDF bilan/compte de
   résultat en pièce jointe).
2. Le Guichet Unique **génère lui-même** un « document de synthèse »
   (PDF, `typeDocument: "PJ_99"`) — **ce n'est pas AxeLCompta qui produit
   ce PDF final**, seulement les données/pièces en amont.
3. Télécharger ce PJ_99 (`GET /api/attachments/{fileId}/file`).
4. Le signer **côté poste client**, avec un certificat RGS — logiciel de
   signature + certificat que le déclarant doit posséder.
5. Reposter le PDF signé, typé `PJ_115` (`POST
   /api/annual_accounts/{id}/attachments`).
6. Confirmer la signature (`POST /api/signatures`, corps
   `{"annualAccount": "/api/annual_accounts/{id}", "signedDocument":
   "/api/attachments/{id}"}`).

**Implication directe pour AxeLCompta** : appeler cette API jusqu'au bout
suppose que le dossier (ou AxeLCompta pour son compte, en tant que
mandataire) dispose d'un certificat qualifié RGS — exactement le sujet
**déjà ouvert par ADR-004** (« prestataire de signature électronique »,
Yousign pressenti, doc 12 §0.1 toujours en devis). ADR-004 parlait de
signature pour les liasses/bilans en général ; ce spike **confirme
concrètement** que c'est une signature *qualifiée* précise (RGS), pas
n'importe quelle signature électronique avancée — à vérifier que Yousign
(ou le prestataire retenu) propose bien ce niveau de certificat avant de
signer un devis pour ce cas d'usage spécifiquement.

## 5. Ce que ça change pour le plan (doc 17 §9 Semaine 4, doc 12)

**Le blocage n'est plus « schéma inconnu » (résolu, §3) mais « signature
qualifiée non disponible »** — même famille de problème que Digifactory
(dépendance externe, pas un bug de notre côté), mais pas contournable par
un simple retest : il faut un vrai certificat RGS, donc une vraie décision
fournisseur (ADR-004), avant de pouvoir appeler `POST /api/signatures`
pour de vrai.

**Ce qui reste possible et utile sans lever ce blocage** (phase 1 de doc
02 §6, confirmée réaliste) : générer le dossier complet — PDF bilan/compte
de résultat déjà produit par le moteur existant (`filings/`, doc 18) +
le payload JSON `content.comptesAnnuels` prêt à poster — pour un dépôt
**manuel** par le client sur `procedures.inpi.fr`, sans jamais appeler
l'API nous-mêmes. C'est un renderer de plus dans `filings/`, pas un
nouveau risque de schéma — **pas construit dans ce spike**, décision de
priorité à prendre avec Louis (le spike répondait à « est-ce qu'on sait
ce qu'il faut construire », pas à « construisons-le »).

**Estimation** (une fois le dictionnaire de données vérifié en détail,
non fait ici) : construire le JSON `comptesAnnuels` + réutiliser le PDF
existant ~0,5-1 jour, du même ordre que les autres renderers `filings/`
(CERFA 2065, FEC). L'intégration API complète (dépôt réel + signature
qualifiée) reste hors de portée tant qu'ADR-004 n'a pas de prestataire
retenu — ne pas l'estimer avant.

## 6. Pas fait dans ce spike

- Compte e-procédures INPI créé/testé en réel (aucun appel HTTP réel,
  contrairement à Digifactory — tout ce doc vient de la lecture du
  contrat public).
- Dictionnaire de données (xlsx) dépouillé champ par champ — nécessaire
  avant toute implémentation réelle du payload `comptesAnnuels`.
- `personnePhysique`/`personneMorale`/`declarant` : structure non détaillée
  ici (probablement proche de ce qui existe déjà pour la formalité de
  création d'entreprise, contrat §1-3, non lu en détail — hors scope de ce
  spike, centré sur §4 dépôt de comptes).
- Confirmation du sens exact de `confidentiel`/`dispenseDepotAnnexes`/
  `depotSimplifie`/`modeExpert` (valeurs possibles, conditions
  d'éligibilité) — champs vus dans l'exemple du contrat mais pas définis
  dedans.
