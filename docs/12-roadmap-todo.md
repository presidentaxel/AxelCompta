# 12 — Roadmap et TODO maître

> Statut : brouillon à valider — Dernière mise à jour : 2026-08-01
> Hypothèse de capacité : 1 à 2 devs. Les durées sont des ordres de grandeur à
> affiner après validation du périmètre ; à 1 dev, étirer d'environ ×1,7.

## Vue d'ensemble des phases

```mermaid
gantt
    dateFormat  YYYY-MM
    title Trajectoire AxeLCompta (ordres de grandeur, 2 devs)
    section Phase 0 — Cadrage
    Validation docs, juridique, données   :p0, 2026-06, 2M
    section Phase 1 — Fondations
    Socle technique + ingestion + ledger  :p1, 2026-08, 4M
    section Phase 2 — Intelligence
    Pipeline règles/ML/LLM + anomalies    :p2, 2026-11, 4M
    section Phase 3 — Production comptable
    Clôture, liasses, FEC, signature      :p3, 2027-02, 4M
    section Phase 4 — Pilote client
    Pilote client, A/B, durcissement      :p4, 2027-05, 3M
    section Phase 5 — Cible
    Partenaire EDI, INPI API, scale       :p5, 2027-08, 6M
```

Jalon de fin de phase = démo + revue de la check-list de phase. On ne commence pas
la phase suivante avec des invariants non tenus.

---

## Phase 0 — Cadrage et dé-risquage (AVANT d'écrire du code produit)

### 0.1 Décisions et juridique
- [ ] Relecture/amendement de toute cette documentation par Louis + associé.
      **Louis : relu (2026-09-02).** Reste l'associé — la case ne se coche
      qu'une fois les deux faits, condition explicite du README avant
      d'écrire du code produit. Prochaine étape (démo doc 17) : go donné,
      démarrage différé — Louis donnera le top départ.
- [x] Structure du pilote confirmée : 1 gestionnaire → ~200 dossiers indépendants, mix SASU/EURL à l'IS + quelques option IR. Reste : collecter la **liste exacte statut par chauffeur** + `tva_recettes_regime` par dossier.
- [x] Positionnement éditeur validé (doc 02 §2.3).
- [ ] CGU/CGV + DPA rédigés (trame au moins).
- [ ] Token Digifactory fonctionnel — bloquant actuel (401, doc 16 §7). Canal exclusif pour septembre 2026.
- [ ] Contrat Bridge direct : pricing, volumes, statut, sandbox — piste parallèle non bloquante, testée après le pilote Digifactory (doc 16 §8).
- [ ] Contrat Rollee : conditions fleet mode, volumes, API sandbox, pricing.
- [ ] Choix prestataire signature (ADR-004) — devis Yousign/Docusign.
- [ ] Décision hébergement prod (ADR-003) après premier échange sécurité banque.
- [ ] **Écrire les ADR 001-006** (docs/adr/) — templates disponibles, à valider.

### 0.2 Les données (chemin critique — démarrer immédiatement)
- [ ] Récupérer un échantillon des 10 ans d'historique.
- [ ] **Vérifier le risque n° 1** : le lien libellé bancaire ↔ imputation existe-t-il ? (doc 07 §2.1)
- [ ] Rapport d'audit du dataset (formats, volume, qualité des labels, droits).
- [ ] Construire la taxonomie du **pack VTC** (~40-80 classes) avec le comptable du client — structurée comme un pack métier dès le départ (doc 03 §3bis).
- [ ] Table de mapping comptes historiques → taxonomie.
- [ ] 500 lignes relues à la main = premier jeu de test gelé.

### 0.3 Spike techniques (timeboxés, 2-3 jours chacun)
- [ ] Spike Digifactory : premier appel réussi (bloqué par 401 à ce jour — doc 16 §7), vérifier présence du SIREN sur `/contacts`, mesurer le poids réel par contact avant chargement des 200 dossiers. Développer contre fixtures en attendant le déblocage.
- [ ] Spike Bridge sandbox direct : connexion, récupération transactions, webhooks — piste parallèle non bloquante, après stabilisation du canal Digifactory (doc 16 §8).
- [ ] Spike baseline ML : TF-IDF + régression logistique **et** embeddings de phrases (`sentence-transformers` multilingue léger) sur le même échantillon → comparer les deux sur le même jeu de test gelé, décider lequel devient le challenger V1 (doc 07 §3.2). Produire en même temps la liste des classes rares et leur politique (doc 07 §3.4).
- [ ] Spike OCR : 30 tickets réels dans Tesseract vs PaddleOCR vs Vision LLM (ADR-005).
- [ ] Spike FEC : générer un FEC minimal et le passer dans « Test Compta Demat ».
- [ ] Maquettes Figma des 3 écrans clés (doc 11 §3) + retours de 2 utilisateurs cibles.

**Critère de sortie Phase 0** : dataset audité, baseline ML mesurée, Digifactory
testé (ou développement mené contre fixtures si le token reste bloqué — doc 16
§7), décisions ADR 001-005 actées, docs validées.

---

## Phase 1 — Fondations (socle + ingestion + cœur comptable)

### 1.1 Socle technique
- [ ] Monorepo (backend + front), Docker Compose dev (Postgres, MinIO).
- [ ] CI complète dès le premier jour (doc 08 §4) — la barrière avant le code, pas après.
- [ ] `core/` : Money (centimes), Result, erreurs, identifiants typés + tests de propriétés.
- [ ] Multi-tenant : modèles tenant (mode portefeuille/mono) + dossier, RLS, middleware d'isolation + suite de tests d'isolation.
- [ ] **Configuration de dossier de premier rang** : statut juridique + régime fiscal + régime TVA + pack métier, matrice doc 06 §7 en données versionnées (toutes les colonnes dans le modèle, IS et option IR opérationnelles). Chaque dossier indépendant, valeurs tenant en simple pré-remplissage.
- [ ] **Option IR bornée** : date de début d'option, décompte des 5 exercices, alertes N-1/N, bascule IS tracée (doc 06 §7) + changement de régime par avenant daté (mécanique générique).
- [ ] **Création de dossiers en masse** : import CSV/XLSX de la configuration (SIREN, forme, régime, dates d'exercice, option IR…) pour onboarder 200 dossiers sans 200 saisies manuelles, avec rapport de validation avant création.
- [ ] Auth B2B : email + MFA TOTP, rôles V1, journal d'audit append-only.
- [ ] Observabilité : logs JSON structurés, Sentry, premières métriques.

### 1.2 Ingestion
- [ ] Archivage brut immuable (hash, horodatage) de tout ce qui entre.
- [ ] **Interface `DataProvider` (ABC)** dans `ingestion/providers/base.py` + types `NormalizedTransaction`, `PlatformSettlement` (doc 13 §2).
- [ ] **`DigifactoryProvider`** (canal actif pour le pilote, doc 16) : contacts/comptes/transactions, sync incrémental sur `since` (pull, pas de webhook), santé des connexions (`paused`/`data_access`/`last_refresh_status`), table de correspondance `contact_nr → dossier_id`, fixtures couvrant les cas doc 16 §9.7.
- [ ] **`BridgeProvider`** direct : piste parallèle non bloquante (sandbox, doc 16 §8), à développer après le pilote Digifactory — items/comptes/transactions, polling + webhooks, santé des connexions, monitoring expiration consentements DSP2.
- [ ] **`RolleeProvider`** : connexion fleet mode, endpoints income/trips/wallet, webhooks `wallet.payout_received`, polling daily fallback, monitoring expiration tokens (doc 13 §3).
- [ ] **`FileImportProvider`** : moteur de profils d'import + parseurs CSV/XLSX/ODS → `RawRow` canonique.
- [ ] **Réconciliation `PlatformSettlement` ↔ `NormalizedTransaction`** : algorithme de matching par montant+date+libellé, états (en attente / réconcilié / revue manuelle), alertes trou (doc 13 §4).
- [ ] **Dashboard consentements** : panneau premier rang listant consentements valides/expirant/expirés pour Digifactory (accès bancaire) et Rollee. Mode relance configurable par tenant (auto ou manuel, doc 14 §2.3) — date d'expiration DSP2 non confirmée exposée côté Digifactory, relance anticipée J-14 potentiellement impossible (doc 16 §6).
- [ ] Normalisation des libellés versionné + tests.
- [ ] Déduplication/idempotence + rapport d'import avec prévisualisation.
- [ ] Quarantaine + UI de correction.
- [ ] Fixtures : un corpus de fichiers par banque rencontrée + corpus de payloads Rollee (vivant, doc 09 §2.2).

### 1.3 Cœur comptable (`ledger`)
- [ ] Plan de comptes PCG embarqué versionné + comptes par dossier + axe analytique.
- [ ] Écritures append-only, partie double, séquences par journal, périodes + verrous (invariants I1-I8 + triggers de protection).
- [ ] Mécanique générique « template + paramètres dossier → écritures équilibrées » (le moteur ne connaît aucun secteur).
- [ ] **Templates pack VTC** (fichiers de données `packs/vtc/`) : carburant (TVA récupération selon véhicule), péage, entretien, LOA (part non déductible), usage personnel (455/108 selon statut), banale charge TTC/HT/TVA.
- [ ] **Templates recettes plateformes** : settlement Rollee → 706 + 44571 (10% ou franchise) + 622x + 44566 (TVA commission selon entité Uber/Bolt — doc 13 §5). Config plateformes dans `packs/vtc/platforms.yaml`.
- [ ] Immobilisations : fiche, plan d'amortissement linéaire, prorata, cession + tests de propriétés (Σ dotations = base).
- [ ] LOA : loyers, part non déductible, suivi hors-bilan, levée d'option.
- [ ] Paramétrage TVA par dossier : `tva_recettes_regime` (assujetti_taux_reduit | franchise), régime déclaration (réel normal — cible unique nouveaux dossiers ; réel simplifié en lecture d'historique seulement, supprimé au 01/01/2027, doc 02 §7bis), surveillance des seuils franchise. Table de règles fiscales versionnée par millésime.
- [ ] Rapprochement bancaire.
- [ ] Dossiers de référence synthétiques → golden tests : SASU IS + Rollee settlements, EURL option IR, dossier franchise TVA, dossier traversant fin d'option IR.
- [ ] **Relecture des templates par un expert-comptable** (prestation, doc 09 §8) — obligatoire avant V1.

### 1.4 Front (en parallèle)
- [ ] Design system de base (tokens, composants, Storybook).
- [ ] Écrans : connexion/MFA, dashboard, liste/fiche dossier, transactions, import avec prévisualisation, journaux/balance (lecture).

**Critère de sortie Phase 1** : un fichier CSV réel importé → écritures manuellement
validées → balance équilibrée et FEC brut généré, le tout démontré sur staging,
couverture ledger ≥ 95 %.

---

## Phase 2 — Intelligence (catégorisation + anomalies)

### 2.1 Règles dures
- [ ] Moteur de règles déclaratives 3 niveaux (système/tenant/dossier) + priorités + journal de collisions.
- [ ] Règles avec tests embarqués obligatoires, exécutés en CI.
- [ ] Premier référentiel : ~100-200 règles système du pack VTC (enseignes carburant, péages, plateformes, assurances…) construites depuis le dataset historique.
- [ ] UI de gestion des règles + création assistée depuis une correction.

### 2.2 ML
- [ ] Pipeline de données : dataset versionné, splits par dossier ET période, pseudonymisation.
- [ ] Baseline (TF-IDF + LogReg) → rapport d'évaluation (doc 07 §4).
- [ ] Challenger LightGBM features mixtes ; calibration isotonic ; seuils par classe.
- [ ] Registry de modèles (table + artefacts S3), promotion champion/candidat, rollback.
- [ ] Intégration runtime : chargement champion, prédiction, explication (top features).
- [ ] Jeu des pièges construit à la main + jeu de test gelé.
- [ ] Monitoring de dérive (taux de correction par classe, confiances).

### 2.3 LLM
- [ ] **Module de pseudonymisation + tests de fuite bloquants** (doc 10 §4) — avant le premier appel réel.
- [ ] Abstraction LLMProvider (Claude/Gemini/OpenAI), sortie JSON schema contrainte, retry/fallback, cache par libellé-type, budget par tenant.
- [ ] Politique de décision ML×LLM (doc 05 §4) + journalisation des motifs d'escalade.

### 2.4 Pipeline assemblé + revue humaine
- [ ] Orchestration 4 étages + auto-validation configurable par tenant.
- [ ] **File de revue** (l'écran clé, doc 11 §3.1) avec raccourcis clavier.
- [ ] Boucle de feedback : corrections → labels → réentraînement mensuel → rapport.
- [ ] Tests de la matrice de scénarios pipeline (doc 09 §2.3).

### 2.5 Anomalies
- [ ] **Profils comportementaux par dossier** (doc 05 §6.2, doc 07 §3.3) : agrégats incrémentaux par catégorie, construits automatiquement à l'import de l'historique.
- [ ] Détecteurs V1 : catégories personnelles, enseigne ambiguë sans/avec ticket incohérent, écart au profil comportemental (3σ), doublons de pièce, double plein.
- [ ] Cycle de vie d'alerte + UI d'instruction (doc 11 §3.2, écart au profil affiché) + templates comptables de résolution (455/108 selon statut du dossier).
- [ ] Jeu d'évaluation : abus historiques connus + abus synthétiques injectés ; mesure rappel/précision.

### 2.6 Justificatifs
- [ ] Stockage WORM, upload UI + adresse email par dossier.
- [ ] Cascade extraction : PDF natif → Factur-X → OCR → Vision LLM, confiance par champ.
- [ ] Matching justificatif↔transaction scoré + file de matching manuel + orphelins.
- [ ] Golden tests OCR (corpus 200 documents annotés).

### 2.7 Accès chauffeur en libre-service (mobile) — cadré dans doc 19, pas encore codé

Contredit le modèle initial : doc 11 §3.3 disait que la page de signature
est « seul écran vu par le chauffeur/gérant » (zéro compte, lien + OTP) ;
doc 04 §4.3 disait que les justificatifs arrivent via le gestionnaire ou par
mail, « vu qu'ils n'ont pas accès à la plateforme ». Louis veut (2026-09-05,
précisé le 2026-09-06) : le chauffeur a son propre compte, relié à ses
propres écritures bancaires, avec une vraie app (mobile) — prend ses tickets
en photo lui-même, répond à des questions de catégorisation simples quand
le système ne sait pas, et peut relier sa propre banque si besoin. **Cadré
et documenté dans [doc 19 — Parcours utilisateur](19-parcours-utilisateur.md)**
(session Claude Code du 2026-09-06) : modèle de compte/onboarding, deux
modes de connexion bancaire par dossier, logique du mode mono-compte. Le
[doc 17](17-plan-demo-backend.md) (plan de démo, pivoté le même jour) en
fait maintenant une des deux interfaces de la démo. Reste à faire : le
code — rien de ceci n'est encore construit. Ne pas confondre avec le flux
Rollee Connect chauffeur (doc 13 §3.3), qui lui est déjà spec depuis le
début.

**Critère de sortie Phase 2** : sur le dataset historique rejoué, ≥ 85 % de
catégorisation automatique à ≥ 97 % de précision, rappel anomalies ≥ 80 %,
zéro fuite au test de pseudonymisation.

---

## Phase 3 — Production comptable complète

- [ ] Checklist de clôture automatisée (doc 06 §5) : CCA/FNP assistées, cadrage TVA, dotations, réintégrations fiscales (plafonds VP, LOA), IS.
- [ ] **Liasse pivot** case-par-case alignée dictionnaire TDFC, formulaires sélectionnés par le statut du dossier : 2065 + 2050/2033 (IS) et 2031 + annexes (option IR) + contrôles de cohérence inter-cases.
- [ ] Renderers : FEC final (CI « Test Compta Demat »), PDF liasse fidèle CERFA, balance/GL/journaux exports, CA3 pré-remplie (CA12 en lecture d'historique seulement, doc 02 §7bis).
- [ ] Dossier de dépôt comptes annuels (Guichet Unique INPI) — génération, dépôt manuel documenté.
- [ ] Dossiers de référence supplémentaires (EURL avec LOA, EURL option IR clôturée, dossier traversant la **fin d'option IR** : exercice N en IR → N+1 en IS) en golden tests — un par colonne opérationnelle de la matrice doc 06 §7.
- [ ] Circuit de validation/relecture interne (statuts, verrous, doc 02 §2.3 — l'humain valide, c'est journalisé).
- [ ] Intégration signature électronique : paquets de documents, lien OTP mobile-first, suivi, relances (doc 11 §3.3).
- [ ] Workflow complet démontré : exercice clôturé → liasse → envoyée → signée → archivée.
- [ ] Deuxième relecture expert-comptable (clôture + liasses).

**Critère de sortie Phase 3** : un exercice complet du dossier de référence clôturé
de bout en bout, liasse conforme, FEC accepté, signature réelle effectuée sur staging.

---

## Phase 4 — Pilote client et durcissement

- [ ] Onboarding du tenant pilote : collecte de la liste statut/régime/TVA par chauffeur, création en masse des ~200 dossiers (chacun paramétré individuellement), profils d'import, reprise d'historique réelle.
- [ ] Adaptation ML au pilote (sur-pondération, doc 07 §3.3) + règles tenant.
- [ ] A/B testing : seuils d'auto-validation, présentation des explications (cadrage initial).
- [ ] Charge : reprise 10 ans (~3 M lignes), clôtures groupées (doc 09 §7).
- [ ] Chaos : pannes LLM/Digifactory/worker → reprise propre prouvée.
- [ ] Test d'intrusion externe + corrections.
- [ ] Runbook incident + exercice sur table (doc 10 §6).
- [ ] Restauration de sauvegarde chronométrée.
- [ ] Questionnaire sécurité du client complété ; SSO si exigé.
- [ ] Période de marche en double : la compta pilote produite en parallèle de
      l'existant pendant 2-3 mois, écarts analysés → c'est LE test de vérité.

**Critère de sortie Phase 4** : 3 mois de marche en double sans écart inexpliqué,
KPIs V1 atteints (doc 01 §6), feu vert du client.

---

## Phase 5 — Trajectoire cible

- [ ] Dossier d'habilitation **Partenaire EDI** déposé (doc 02 §5) : pièces administratives, clé publique, RDV correspondant régional.
- [ ] Génération EDIFACT/TDFC depuis la liasse pivot + attestation de conformité EDIFICAS.
- [ ] Télétransmission test puis réelle (TDFC, EDI-TVA) ; en attendant : intégration partenaire EDI tiers si le volume le justifie.
- [ ] API INPI Guichet Unique pour le dépôt des comptes.
- [ ] Onboarding industrialisé d'un nouveau client : < 2 semaines données → modèle adapté (doc 07 §3.3).
- [ ] **Nouveaux packs statut** selon la demande : EI au réel, micro-entreprise (livre des recettes + jauges de seuils), BNC/2035… (matrice doc 06 §7 — données et templates, pas de refonte).
- [ ] **Nouveaux packs métier** au premier client hors VTC : taxonomie, règles, templates du secteur.
- [ ] **UI mode mono-entreprise** : habillage direct sur le dossier unique (doc 11 §1bis) — la couche dossier existe déjà, on retire la couche portefeuille.
- [ ] Ingestion Factur-X via Plateformes Agréées (réforme 2026-2027).
- [ ] Étude certification NF 203 ; SSO entreprise ; mode sombre ; selon demande.

---

## Backlog transverse permanent (jamais « fini »)

- Chaque bug prod cœur comptable → post-mortem + fixture de non-régression (doc 09 §9).
- Veille millésimes fiscaux (TDFC, taux, plafonds CO2) → mise à jour des tables versionnées + goldens.
- Veille jurisprudence ordonnance 1945 (doc 02).
- Revue mensuelle des motifs d'escalade LLM → nouvelles règles.
- Échantillonnage mensuel des prompts sortants (contrôle pseudonymisation).
- Renouvellement dépendances (PR auto hebdo/mensuelle).

## Règles de pilotage du projet

1. **Le chemin critique est la donnée, pas le code** : l'audit du dataset (0.2) et
   la marche en double (4) sont les deux moments de vérité du projet.
2. À chaque fin de phase : revue des KPIs, mise à jour des docs, go/no-go explicite.
3. Tout ce qui touche au réglementaire (FEC, liasse, TVA) est validé par un
   expert-comptable avant production — budget récurrent assumé.
4. Périmètre V1 défendu agressivement : tout ce qui n'est pas dans les docs 01-12
   passe par une décision écrite (ADR ou mise à jour de doc), pas par un « vite fait ».
