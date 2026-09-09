# 16 — Intégration Digifactory (source bancaire)

> **Statut : spec confirmée par le fournisseur, non encore vérifiée par appel réel.**
> Le token retourne actuellement un 401 (voir §7). Tout ce qui est marqué
> ⚠️ *à confirmer* vient de la description de Pierre BERTOLA et n'a pas été
> observé dans une réponse réelle.
> Dernière mise à jour : 2026-09-01.

> **Phasage : Digifactory est le canal exclusif pour septembre 2026.**
> Bridge reste la source de données de base (Digifactory n'est qu'un tampon qui
> agrège les mêmes données Bridge par contact) — on ne retire rien de ce qui
> existe sur Bridge dans les autres docs. L'accès Bridge direct (sandbox, §8)
> est une piste parallèle non bloquante, testée après la période Digifactory,
> pas en concurrence avec elle. `DataProvider` (doc 13 §2) est conçu pour
> encaisser les deux sans changement ailleurs dans la chaîne d'ingestion.

---

## 1. Contexte et décision

L'accès aux données bancaires **ne se fait pas en direct auprès de Bridge**
pour le moment. Digifactory (contact : Pierre BERTOLA) est déjà client Bridge,
agrège les données par contact, et nous expose une API dédiée construite à
notre demande.

**Conséquences :**

- On implémente un `DigifactoryProvider`, pas un `BridgeProvider`, dans un
  premier temps. Le pattern DataProvider (doc 13 §2) absorbe le changement :
  rien d'autre ne bouge dans la chaîne d'ingestion. Un `BridgeProvider` direct
  reste prévu (§8) mais n'est pas développé tant que Digifactory couvre le
  besoin du pilote.
- Pas de webhook. Le rafraîchissement est en **pull**, à notre initiative.
- Digifactory ne peut pas nous fournir de credentials Bridge : leur plateforme
  n'expose qu'un seul couple `client_id`/`client_secret`, utilisé par leur
  propre application. Un accès Bridge direct, s'il est ouvert un jour, passera
  par une application séparée (voir §8).
- L'identifiant pivot pour le canal Digifactory est le **`nr` de contact
  Digifactory**, distinct du `bridge_item_id` déjà présent dans le CSV
  d'onboarding (doc 14 §1.2). Les deux colonnes coexistent : `bridge_item_id`
  reste réservé au jour où le provider Bridge direct sera actif.

---

## 2. Accès

**Base URL :** `https://entrepreneur.digifactory.fr/api/bridge`

**Authentification :** en-tête `Authorization: Bearer <token>`

Le token est un secret de 64 caractères, transmis hors bande. Il ne doit
jamais être commité ni écrit dans un fichier versionné — lecture par variable
d'environnement uniquement (`DIGIFACTORY_TOKEN`).

Cycle de vie du token (durée de validité, rotation, scope, procédure en cas de
fuite) : **non documenté**, question posée au fournisseur, sans réponse à ce
jour. Traiter comme révocable à tout moment : l'échec d'authentification doit
être un cas géré explicitement, pas une exception qui remonte brute.

---

## 3. Routes

Les quatre routes fournies, telles que communiquées :

```
GET /contacts
GET /accounts/{contactNr}
GET /transactions/{contactNr}
GET /categories
```

Toutes en `GET`, avec l'en-tête `accept: */*`.

### 3.1 `/transactions/{contactNr}`

**Paramètres :**

| Paramètre | Format | Usage |
|---|---|---|
| `since` | `YYYY-MM-DD HH:MM:SS` | Filtre sur `updated_at`. **À utiliser pour tout sync courant.** |
| `from` / `to` | `YYYY-MM-DD HH:MM:SS` | Filtre sur la date d'opération. Rattrapages ponctuels uniquement. |

**`since` est le mode nominal.** Il a été demandé et implémenté spécifiquement
parce que `from`/`to` filtrent sur la date de transaction : une opération du 3
corrigée par la banque le 12 (pending → booked, montant ajusté, suppression)
n'apparaîtrait jamais dans une fenêtre glissante sur la date d'opération. Le
sync incrémental doit donc s'appuyer sur `since`, en persistant le `updated_at`
max observé au dernier passage.

**Forme de la réponse :** objet indexé par `accountId`.

```json
{
  "<accountId>": [ { ...transaction }, ... ],
  "<accountId>": [ ... ]
}
```

⚠️ *À confirmer.* Pierre a initialement décrit une indexation par nom de banque
(`"Swan"`, `"Bourso"`), puis corrigé : c'est bien l'`accountId`. Le parsing doit
néanmoins **ne pas dépendre de la clé** — lire `account_id` sur chaque
transaction si le champ y est présent, et ne se rabattre sur la clé que sinon.

### 3.2 `/accounts/{contactNr}`

Réponse indexée par identifiant de compte. Champs annoncés :

```
id  name  item_id  provider_id  pro  data_access  paused  iban
balance  type  currency_code  updated_at  last_refresh_status
```

Plus les objets liés **`item`** (dates de rafraîchissement) et **`provider`**,
ajoutés par le fournisseur sans qu'on les demande.

### 3.3 `/contacts`

Liste des contacts. Le champ `nr` est l'identifiant pivot.

⚠️ **Vérifier au premier appel réussi si le SIREN est présent.** C'est le point
de jointure vers nos dossiers. En son absence, le mapping `nr → dossier_id` est
manuel sur ~200 chauffeurs et doit être stocké dans une table de correspondance
explicite.

### 3.4 `/categories`

Référentiel de catégories Bridge (Digifactory se contente de le relayer).

**À traiter comme une feature d'entrée du modèle de catégorisation, jamais
comme une vérité comptable.** Un `category_id` Bridge ne détermine pas un compte
du PCG. Il alimente le classifieur au même titre que le libellé ; il ne
court-circuite ni les règles ni la validation humaine.

---

## 4. Schéma transaction

Champs confirmés disponibles par le fournisseur (nomenclature Bridge) :

| Champ | Rôle | Criticité |
|---|---|---|
| `id` | Clé de déduplication | **Bloquant** |
| `provider_description` | Libellé brut de la banque | **Bloquant** — matière première de la catégorisation |
| `clean_description` | Libellé normalisé Bridge | Complément, ne remplace pas le brut |
| `amount` | Montant | **Bloquant** |
| `currency_code` | Devise | Requis |
| `date` | Date d'opération | Requis |
| `booking_date` / `transaction_date` / `value_date` | Dates détaillées | Selon disponibilité |
| `updated_at` | Sync incrémental | **Bloquant** |
| `deleted` | Transaction annulée | Requis — ne jamais comptabiliser |
| `future` | Transaction projetée | Requis — ne jamais comptabiliser |
| `operation_type` | Type d'opération | Feature |
| `category_id` | Catégorie Bridge | Feature uniquement |
| `account_id` | Compte bancaire | **Bloquant** — rapprochement |

---

## 5. Contraintes d'implémentation

**Montants.** Si `amount` arrive en float JSON, convertir en `Decimal` **dès le
parsing**, avant toute arithmétique. Jamais de float binaire sur de l'argent
(doc 08 §2, règle de lint bloquante). Le `Decimal` n'est qu'une étape
intermédiaire : la sortie du provider reste `NormalizedTransaction.montant_centimes`
(int, doc 04 §5), conforme au type `Money` du reste du système. Vérifier au
premier appel si l'unité source est l'euro ou le centime.

**Dates.** Le format annoncé (`YYYY-MM-DD HH:MM:SS`) est sans fuseau, et le
fournisseur a lui-même mentionné un décalage horaire. Normaliser en UTC à
l'ingestion, en documentant le fuseau source retenu. ⚠️ *À confirmer sur une
réponse réelle.*

**Déduplication.** Clé = `id` de transaction. Un `id` déjà connu dont
l'`updated_at` a changé est une **mise à jour**, pas un doublon : il doit
déclencher la révision de l'écriture associée, pas être ignoré silencieusement.

**Pagination.** Aucune pagination documentée sur ces routes. Le `since` borne le
volume en régime courant, mais le **premier appel sans filtre peut être
volumineux**. Prévoir un découpage `from`/`to` par mois en repli, et mesurer le
poids réel par contact avant de lancer un chargement sur 200 dossiers.

**Rate limit.** Non communiqué. Le fournisseur a explicitement demandé d'éviter
un volume de requêtes élevé et des réponses massives. Implémenter un backoff et
sérialiser les appels par défaut plutôt que de paralléliser.

**Santé de connexion.** La combinaison `paused` + `data_access` +
`last_refresh_status` distingue un chauffeur inactif d'une connexion cassée.
C'est ce qui alimente le dashboard consentements (doc 14 §2.2). Un compte dont
la connexion est rompue doit produire une alerte, jamais un silence
interprétable comme une absence d'activité.

---

## 6. Ce qui reste ouvert

| Sujet | Impact |
|---|---|
| Profondeur d'historique conservée chez Digifactory | Détermine si la reprise d'antériorité passe par cette API ou uniquement par les FEC |
| Date d'expiration du consentement DSP2 exposée ? | Sans elle, on constate la panne au lieu de l'anticiper (relance J-14 impossible, doc 14 §2.3) |
| Cycle de vie du token | Rotation, révocation, procédure d'incident |
| Chaîne de sous-traitance RGPD | chauffeur → Bridge → Digifactory → nous. Le consentement DSP2 signé couvre-t-il la retransmission ? Art. 28 à trois parties. **Non traité, à instruire en phase 0** (doc 02 §3, doc 10). |
| Qui gère le lien Bridge Connect pour un nouveau chauffeur | Digifactory possède la relation Bridge ; pas confirmé si l'ouverture d'une nouvelle connexion pour un chauffeur pilote passe par eux ou reste hors de notre contrôle (doc 14 §1.5). |

---

## 7. Statut du token (bloquant à ce jour)

Le token reçu retourne un **401** sur `/contacts` :

```json
{"error":{"exception":"UnauthorizedException","code":401,
 "reason":"An authentication is mandatory for this action"}}
```

Écarté côté client : longueur correcte (64 caractères), aucun caractère
parasite, deux clients HTTP distincts, avec et sans préfixe `Bearer`. TLS et
routage fonctionnent — l'échec est bien au niveau de l'authentification côté
serveur. Signalé au fournisseur avec les tags de trace, en attente.

**En conséquence : développer contre des fixtures.** Le `DigifactoryProvider`
et ses tests peuvent être écrits intégralement contre le schéma ci-dessus.
Quand le token fonctionnera, les fixtures sont remplacées par des réponses
réelles capturées, et l'écart de schéma est traité à ce moment-là. Ne pas
attendre le déblocage pour commencer.

**Retest du 2026-09-07** : toujours 401, sur `/contacts` (avec et sans
préfixe `Bearer`) et sur `/categories`. Mêmes constats côté client
qu'au 01/09 (token correct, TLS/routage OK, échec au niveau
authentification serveur) — rien n'a changé en un mois. Document de
relance envoyé à Pierre BERTOLA avec tags de trace :
[2026-09-07-relance-digifactory.md](2026-09-07-relance-digifactory.md).

**Statut au 2026-09-08 : mail envoyé, en attente de réponse.** Pierre
BERTOLA est basé au Japon — décalage horaire important, délai de réponse
normal de quelques jours à compter de là, pas un signe que la relance s'est
perdue. Ne pas relancer une deuxième fois avant d'avoir laissé passer ce
délai.

**Réponse reçue (2026-09-09).** Pierre doit renvoyer des `curl` (à
confirmer lesquels — vraisemblablement des appels fonctionnels de son côté,
ou un jeton/une config à retester) **vendredi 2026-09-11**. Le token reste
401 jusque-là — rien à retester avant cette date. Session suivante :
vérifier si les curls sont arrivés et reprendre le retest de ce §7 à partir
d'eux.

---

## 8. Accès Bridge direct (piste parallèle, non bloquante, après le pilote Digifactory)

Souhaité comme chemin de repli, pour ne pas dépendre d'un tiers unique sur une
brique aussi centrale que l'ingestion bancaire. Le fournisseur ne peut pas le
fournir et a raison de ne pas partager son secret de production.

Le chemin passe par une **application Bridge distincte** (chaque application a
son propre couple `client_id`/`client_secret`, aucune interférence avec la
production Digifactory), à ouvrir via l'équipe Bridge. Commencer par le
**sandbox**, qui débloque les spikes sans décision préalable. Ces tests
sandbox sont prévus **après** la période de test full-Digifactory de septembre
2026, pas en parallèle : Digifactory reste le seul canal actif ce mois-ci.

Point d'attention : le dashboard Bridge applique un **filtrage par IP**. Les IP
de sortie de la plateforme doivent être fixes et connues avant toute demande.

---

## 9. À faire côté code

1. `DigifactoryProvider` implémentant l'interface `DataProvider` (doc 13 §2).
2. Sync incrémental sur `since`, avec persistance du `updated_at` max par contact.
3. Normalisation à l'ingestion : `Decimal` pour les montants, UTC pour les dates.
4. Filtrage systématique de `deleted` et `future` avant écriture comptable.
5. Table de correspondance `contact_nr → dossier_id`.
6. Monitoring de fraîcheur et de santé de connexion par compte.
7. Fixtures et tests couvrant : transaction mise à jour rétroactivement,
   transaction supprimée, contact multi-comptes dans la même banque, connexion
   en échec, réponse vide.
8. Ajouter `digifactory_contact_nr` au CSV d'onboarding et à la documentation
   associée (doc 14 §1.2), **en plus de** `bridge_item_id` qui reste réservé au
   futur provider Bridge direct (§8) — pas de renommage, les deux colonnes
   coexistent.
