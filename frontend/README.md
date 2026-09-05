# frontend/

TypeScript / React / Next.js — back-office riche + pages de signature
publiques en SSR (doc 03 §2). Design system : voir [DESIGN.md](../DESIGN.md).

**Dépendances :** consomme uniquement `api/` (backend), aucun accès direct
à la base ou aux modules métier.

## Les trois écrans clés (V1, doc 11 §3)

Détail complet dans [doc 11](../docs/11-ux-ui.md) — l'UI s'adapte de 1 à 200
dossiers et au statut de chaque dossier (doc 11 §1bis).

## Statuts

- **Démo (doc 17 §6, semaine 4 seulement)** : **pas une vraie UI.** Un
  rapport HTML/notebook qui montre les étapes du pipeline (transaction →
  settlement → réconciliation → écriture → liasse), juste pour le récit
  visuel de la démo.
- **V1 (doc 12, phase 3-4)** : Next.js complet, design system (DESIGN.md),
  maquettes Figma validées avec 2 utilisateurs cibles (doc 12 §0.3).

## Doc de référence

[doc 11](../docs/11-ux-ui.md) (UX/UI complet),
[DESIGN.md](../DESIGN.md) (design system : tokens, composants, Do's & Don'ts),
[doc 17 §6](../docs/17-plan-demo-backend.md#6-semaine-par-semaine).
