"""role web et policies RLS

Revision ID: 87fc7238e52e
Revises: ca7b37bba581
Create Date: 2026-09-22 22:07:26.416786

Doc 12 §1.1 : isolation multi-tenant en profondeur, pas seulement
applicative (`_verifier_acces_dossier` dans `demo_api.py`, doc 19 §8bis).

Deux rôles Postgres à partir de cette migration :
- `user` (inchangé) : propriétaire des tables, utilisé par les migrations
  et les scripts d'administration (`demo_seed`, `synchro_digifactory`,
  `notifier`) — jamais soumis aux policies RLS (comportement par défaut
  Postgres pour le propriétaire d'une table, pas de FORCE ROW LEVEL
  SECURITY ici : ces scripts traitent volontairement plusieurs
  dossiers/tenants à la fois, ce n'est pas un contournement).
- `axelcompta_web` (nouveau) : utilisé uniquement par `demo_api.py` (le
  seul point qui sert de vraies requêtes HTTP avec une identité par
  requête). Ni propriétaire ni superuser : soumis aux policies par
  construction. Droits accordés au plus juste des besoins actuels de
  `demo_api.py` (doc `axelcompta/core/rls.py`) : SELECT sur les tables
  qu'il lit, INSERT sur `decisions_humaines` (seule écriture Postgres
  faite par l'API). Les tables non lues par l'API ont quand même leurs
  policies posées (cohérence du modèle), mais aucun GRANT vers
  `axelcompta_web` tant qu'aucune route n'en a besoin — sans GRANT, une
  policy est sans effet, mais ne fait pas de mal non plus.

Le contexte (`app.dossier_id`/`app.tenant_id`) est posé par requête via
`set_config(..., true)` (portée transaction, jamais fuité entre deux
requêtes qui réutiliseraient la même connexion du pool) — voir
`axelcompta/core/rls.py` et le middleware `demo_api.py`.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '87fc7238e52e'
down_revision: Union[str, Sequence[str], None] = 'ca7b37bba581'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mot de passe de développement, cohérent avec `user`/`password` déjà en
# clair dans docker-compose.yml/.env.example — cette base ne contient que
# des données synthétiques (doc 17 §4). À changer avant tout déploiement
# sur une vraie base (doc 10, hors scope démo).
_MOT_DE_PASSE_WEB = "web_password_dev"

# Tables où une ligne appartient directement à un dossier (colonne
# `dossier_id`) : la fonction `axelcompta_dossier_visible` centralise la
# règle d'accès (indiv sur son propre dossier, gestionnaire sur tout son
# portefeuille) une seule fois plutôt que de la dupliquer par policy.
_TABLES_PAR_DOSSIER = (
    "ecritures",
    "decisions_humaines",
    "annotations_dev",
    "propositions_categorisation",
    "notifications_envoyees",
    "ingestion_brut",
    "curseurs_synchro",
    "quarantaine_ingestion",
)

# Sous-ensemble réellement lu/écrit par `demo_api.py` aujourd'hui (voir le
# docstring ci-dessus) — seules ces tables reçoivent un GRANT vers
# `axelcompta_web`.
_TABLES_LUES_PAR_API = ("dossiers", "tenants", "ecritures", "lignes_ecriture",
                         "propositions_categorisation", "decisions_humaines")
_TABLE_ECRITE_PAR_API = "decisions_humaines"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'axelcompta_web') THEN
            CREATE ROLE axelcompta_web LOGIN PASSWORD '{_MOT_DE_PASSE_WEB}';
          END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO axelcompta_web")

    # `dossiers` : visible si l'indiv y a son propre dossier_id, ou si le
    # gestionnaire y a son tenant_id — les deux liens indépendants du
    # modèle de compte (doc 03 §7).
    op.execute("ALTER TABLE dossiers ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY dossiers_isolation ON dossiers
          FOR ALL TO axelcompta_web
          USING (
            id = current_setting('app.dossier_id', true)
            OR tenant_id = current_setting('app.tenant_id', true)
          )
          WITH CHECK (
            id = current_setting('app.dossier_id', true)
            OR tenant_id = current_setting('app.tenant_id', true)
          )
        """
    )

    # `tenants` : visible seulement pour son propre gestionnaire.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenants_isolation ON tenants
          FOR ALL TO axelcompta_web
          USING (id = current_setting('app.tenant_id', true))
          WITH CHECK (id = current_setting('app.tenant_id', true))
        """
    )

    # Fonction partagée : une ligne "appartenant" à dossier_id est visible
    # si et seulement si ce dossier l'est lui-même (règle ci-dessus) —
    # STABLE, pas SECURITY DEFINER : elle s'exécute avec les droits de
    # l'appelant, donc soumise à la policy `dossiers_isolation` comme
    # n'importe quelle autre requête du même rôle. Pas de contournement.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION axelcompta_dossier_visible(d_id varchar)
        RETURNS boolean
        LANGUAGE sql STABLE
        AS $$
          SELECT EXISTS (SELECT 1 FROM dossiers WHERE id = d_id)
        $$
        """
    )

    for table in _TABLES_PAR_DOSSIER:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
              FOR ALL TO axelcompta_web
              USING (axelcompta_dossier_visible(dossier_id))
              WITH CHECK (axelcompta_dossier_visible(dossier_id))
            """
        )

    # `lignes_ecriture` n'a pas de `dossier_id` propre (FK vers
    # `ecritures` seulement) : visible si son écriture parente l'est,
    # exactement le même mécanisme qu'une jointure normale respecterait.
    op.execute("ALTER TABLE lignes_ecriture ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY lignes_ecriture_isolation ON lignes_ecriture
          FOR ALL TO axelcompta_web
          USING (EXISTS (SELECT 1 FROM ecritures e WHERE e.id = lignes_ecriture.ecriture_id))
          WITH CHECK (EXISTS (SELECT 1 FROM ecritures e WHERE e.id = lignes_ecriture.ecriture_id))
        """
    )

    for table in _TABLES_LUES_PAR_API:
        op.execute(f"GRANT SELECT ON {table} TO axelcompta_web")
    op.execute(f"GRANT INSERT ON {_TABLE_ECRITE_PAR_API} TO axelcompta_web")


def downgrade() -> None:
    """Downgrade schema."""
    for table in (*_TABLES_LUES_PAR_API, _TABLE_ECRITE_PAR_API):
        op.execute(f"REVOKE ALL ON {table} FROM axelcompta_web")

    op.execute("DROP POLICY IF EXISTS lignes_ecriture_isolation ON lignes_ecriture")
    op.execute("ALTER TABLE lignes_ecriture DISABLE ROW LEVEL SECURITY")

    for table in _TABLES_PAR_DOSSIER:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP FUNCTION IF EXISTS axelcompta_dossier_visible(varchar)")

    op.execute("DROP POLICY IF EXISTS tenants_isolation ON tenants")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS dossiers_isolation ON dossiers")
    op.execute("ALTER TABLE dossiers DISABLE ROW LEVEL SECURITY")

    op.execute("REVOKE USAGE ON SCHEMA public FROM axelcompta_web")

    # Le rôle lui-même n'est PAS supprimé ici, volontairement : `CREATE
    # ROLE` est une opération de cluster Postgres, pas de base — trouvé en
    # testant (doc 09 §4, `test_upgrade_puis_downgrade_sont_symetriques`
    # tourne sur `axelcompta_test`, qui partage le même cluster que
    # `axelcompta_dev`). `DROP ROLE` échoue avec `DependentObjectsStillExist`
    # tant que le rôle a des droits dans une AUTRE base du même cluster (ici
    # `axelcompta_dev`, jamais downgradé en parallèle). Le laisser trainer
    # sans droits ni policies est inoffensif ; `CREATE ROLE ... IF NOT
    # EXISTS` du upgrade le retrouve tel quel, ré-idempotent.
