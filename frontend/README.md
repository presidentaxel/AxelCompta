# frontend/

TypeScript / React / Next.js (App Router) — back-office riche + pages de
signature publiques en SSR (doc 03 §2). Design system : voir
[DESIGN.md](../DESIGN.md).

**Dépendances :** consomme `axelcompta.demo_api` pour la démo (voir
Statuts ci-dessous) ; consommera uniquement `api/` (backend réel) en V1,
aucun accès direct à la base ou aux modules métier.

## Démarrer en local (démo)

Deux process, dans deux terminaux :

```bash
# 1. L'API démo (backend/)
cd backend && source .venv/bin/activate
uvicorn axelcompta.demo_api:app --reload --port 8000

# 2. Le frontend (frontend/)
cd frontend && npm install && npm run dev
```

Puis ouvrir `http://localhost:3000`. `NEXT_PUBLIC_API_BASE_URL` (défaut
`http://localhost:8000`) est configurable via `.env.local` (voir
`.env.example`).

## Les trois écrans clés (V1, doc 11 §3)

Détail complet dans [doc 11](../docs/11-ux-ui.md) — l'UI s'adapte de 1 à 200
dossiers et au statut de chaque dossier (doc 11 §1bis). Le parcours
chauffeur (mobile) est cadré dans [doc 19](../docs/19-parcours-utilisateur.md).

## Statuts

- **Démo (doc 17 §9, pivot 2026-09-06)** : **une vraie UI**, plus un rapport
  HTML statique — Next.js + Tailwind, tokens `DESIGN.md`, consomme
  `axelcompta.demo_api` (lecture seule) en direct. Fait : tableau de bord
  (3 dossiers) + fiche dossier (liste des transactions, badge « à
  trancher » sur le compte d'attente 471). **Pas fait** : la vraie décision
  humaine sur la file de revue (accepter/reclasser, doc 11 §3.1/§3.2) —
  l'API ne sert que du GET pour l'instant (doc 17 §9 semaine 2, suite) ;
  l'interface chauffeur (mobile, doc 19).
- **V1 (doc 12, phase 3-4)** : Next.js complet sur `api/` (le vrai backend,
  auth/MFA, multi-tenant), design system (`DESIGN.md`), maquettes Figma
  validées avec 2 utilisateurs cibles (doc 12 §0.3).

## Doc de référence

[doc 11](../docs/11-ux-ui.md) (UX/UI complet),
[doc 19](../docs/19-parcours-utilisateur.md) (parcours gestionnaire/chauffeur),
[DESIGN.md](../DESIGN.md) (design system : tokens, composants, Do's & Don'ts),
[doc 17 §9](../docs/17-plan-demo-backend.md#9-semaines-et-jalons).
