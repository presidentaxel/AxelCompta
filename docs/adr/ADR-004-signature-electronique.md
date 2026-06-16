# ADR-004 — Prestataire de signature électronique : Yousign (pressenti)

**Date :** 2026-06-16
**Statut :** en attente de devis — décision finale à prendre en phase 0
**Décideurs :** Louis Vedovato

## Contexte

Le circuit de validation finale (doc 11 §3.3) nécessite une signature électronique qualifiée ou avancée eIDAS pour les liasses fiscales et bilans. La signature est déclenchée côté AxeLCompta et réalisée par le gérant du dossier (chauffeur) sur une page mobile-first sans création de compte.

## Contraintes

- **Parcours sans compte** : le signataire accède via un lien OTP email, sans s'inscrire.
- **Mobile-first** : les chauffeurs signent depuis leur téléphone.
- **API propre** : l'intégration doit être pilotable programmatiquement (génération de liens, webhooks sur événements de signature, archivage des preuves).
- **eIDAS** : niveau avancé (simple suffisant pour nos documents, qualifié si exigé par le client).
- **Hébergement France/UE** : cohérent avec ADR-003.

## Candidats évalués

| Critère | Yousign | Docusign |
|---------|---------|---------|
| Société française | ✅ | ❌ (US) |
| API REST moderne | ✅ | ✅ |
| Parcours sans compte | ✅ | ✅ |
| Pricing (petits volumes) | ✅ Abordable | ⚠️ Élevé |
| eIDAS avancé | ✅ | ✅ |
| Archivage preuve inclus | ✅ | ✅ |

## Décision provisoire

**Yousign** est le candidat principal. Société française, API propre, pricing adapté aux volumes V1 (~200 signatures/an en démarrage). À confirmer par un devis et une POC de l'intégration en phase 0.

## Action requise

- [ ] Demander un devis Yousign (volume estimé : 200-400 signatures/an en V1)
- [ ] POC : générer un lien de signature, capter le webhook "signé", récupérer le document signé avec sa preuve
- [ ] Vérifier que le client pilote n'a pas de prestataire imposé
