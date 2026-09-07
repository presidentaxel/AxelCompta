# frontend/

TypeScript / React / Next.js (App Router) — back-office riche + pages de
signature publiques en SSR (doc 03 §2). Design system : voir
[DESIGN.md](../DESIGN.md).

**Dépendances :** consomme `axelcompta.demo_api` pour la démo (voir
Statuts ci-dessous) ; consommera uniquement `api/` (backend réel) en V1,
aucun accès direct à la base ou aux modules métier.

## Démarrer en local (démo)

**Changement 2026-09-07** : l'API démo a maintenant besoin d'un Postgres
démarré (persistance réelle des décisions humaines, doc 17 §9 bloc A) —
avant, elle tournait entièrement en mémoire.

```bash
# 0. La base (une fois) : depuis backend/
docker compose up -d db
source .venv/bin/activate && alembic upgrade head

# 1. L'API démo (backend/)
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

- **Démo (doc 17 §9)** : **une vraie UI**, plus un rapport HTML statique —
  Next.js + Tailwind, tokens `DESIGN.md`, consomme `axelcompta.demo_api`
  en direct. Fait côté back (2026-09-07) : `POST .../decision` accepte/
  reclasse une écriture « à trancher » pour de vrai (workflow testé,
  persistance Postgres réelle, doc 17 §9 bloc A/C) — testé en HTTP réel
  (`curl`), pas seulement en unitaire. **Pas fait côté front** : aucun
  écran ni bouton n'appelle encore cet endpoint — la fiche dossier reste
  un affichage en lecture, l'action de trancher n'existe que côté API pour
  l'instant. C'est la suite immédiate. L'interface chauffeur (mobile, doc
  19) n'est pas commencée non plus.
- **V1 (doc 12, phase 3-4)** : Next.js complet sur `api/` (le vrai backend,
  auth/MFA, multi-tenant), design system (`DESIGN.md`), maquettes Figma
  validées avec 2 utilisateurs cibles (doc 12 §0.3).

## Doc de référence

[doc 11](../docs/11-ux-ui.md) (UX/UI complet),
[doc 19](../docs/19-parcours-utilisateur.md) (parcours gestionnaire/chauffeur),
[DESIGN.md](../DESIGN.md) (design system : tokens, composants, Do's & Don'ts),
[doc 17 §9](../docs/17-plan-demo-backend.md#9-semaines-et-jalons).
