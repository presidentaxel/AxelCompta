"""revoque les droits des roles Supabase sur public

Revision ID: e4c7a9d25b13
Revises: d8b41c6e0a27
Create Date: 2026-09-24 21:00:00.000000

Depuis le 2026-09-24 la base applicative est sur Supabase (ADR-003). Supabase
donne par défaut à `anon` et `authenticated` tous les droits sur ce qui est
créé dans `public`, pour son API REST (PostgREST). On ne l'utilise pas
(ADR-003 : jamais PostgREST) : seul `axelcompta_web` doit lire ces tables.
La RLS les bloquait déjà (aucune policy pour ces rôles), ceci retire la
deuxième porte. Sans effet sur un Postgres local, où ces rôles n'existent pas.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e4c7a9d25b13"
down_revision: str | Sequence[str] | None = "d8b41c6e0a27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLES = ("anon", "authenticated")


def upgrade() -> None:
    for role in _ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role};
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role};
                REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {role};
              END IF;
            END
            $$;
            """
        )


def downgrade() -> None:
    # Pas de ré-octroi : rendre ces droits à des rôles qu'on n'utilise pas
    # n'a aucun intérêt et rouvrirait la porte.
    pass
