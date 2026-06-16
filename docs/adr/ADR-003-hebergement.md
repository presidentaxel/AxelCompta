# ADR-003 — Hébergement production : OVHcloud

**Date :** 2026-06-16
**Statut :** accepté (à confirmer après questionnaire sécurité du client)
**Décideurs :** Louis Vedovato

## Contexte

AxeLCompta traite des données bancaires et fiscales de personnes morales françaises. Le client pilote est une entité du secteur financier (gestionnaire de chauffeurs VTC avec comptes bancaires pros). Ce type de client soumet généralement un questionnaire sécurité fournisseur qui inclut des exigences sur la localisation des données.

## Décision

**Production sur OVHcloud (France).** Environnements de dev et staging sur DigitalOcean (acceptable — pas de données réelles).

## Justification

| Critère | OVHcloud | DigitalOcean |
|---------|----------|--------------|
| Localisation données France | ✅ Oui | ⚠️ UE possible mais société US (CLOUD Act) |
| Argument commercial banque | ✅ Fort | ⚠️ Friction probable |
| Postgres managé | ✅ | ✅ |
| Object Storage S3 | ✅ | ✅ (Spaces) |
| DX / simplicité | Moyenne | Très bonne |

Le CLOUD Act américain permet aux autorités US d'accéder aux données hébergées par des sociétés US, même en Europe. Pour un client du secteur bancaire ou parabancaire, cet argument est rédhibitoire.

## Conséquences

- Déploiement prod : OVHcloud Managed Kubernetes ou instances dédiées + Managed Postgres + Object Storage.
- Dev/staging : DigitalOcean (coût réduit, DX supérieure).
- Si un futur client exige SecNumCloud : OVHcloud est la seule option marché ayant cette qualification en France. À chiffrer à ce moment-là.
- **À confirmer** après réception du questionnaire sécurité du client pilote : ses exigences précises peuvent modifier cette décision (ex. hébergement dédié, pas de mutualisé).
