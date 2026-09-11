"""0001 — Database roles and RLS foundation.

Creates the two-role RLS model:
  * `app_user`     NOLOGIN         — target of every RLS policy.
  * `app_migrator` NOLOGIN BYPASSRLS — migrations; exempt from RLS.

The application connects as `school_os_app` (member of `app_user`); Alembic
connects as `school_os_migrator` (member of `app_migrator`, BYPASSRLS). A
superuser is never used in an application connection string.

Operational note: local dev pre-creates the login roles in
`scripts/db/init.sh` (as the container superuser). In production, ops creates
equivalent roles out-of-band. This migration re-declares them idempotently so
the schema is self-describing and works when the migrator itself may create
roles.
"""
from __future__ import annotations

from alembic import op

revision = "0001_db_roles_and_rls_setup"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user NOLOGIN;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_migrator') THEN
                BEGIN
                    CREATE ROLE app_migrator NOLOGIN BYPASSRLS;
                EXCEPTION WHEN insufficient_privilege THEN
                    -- Not a superuser: create without BYPASSRLS. The login role
                    -- school_os_migrator carries BYPASSRLS directly.
                    CREATE ROLE app_migrator NOLOGIN;
                END;
            END IF;
        END $$;
        """
    )

    # Attach the login roles as members so RLS policies bound TO app_user apply
    # to the application connection.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'school_os_app') THEN
                EXECUTE 'GRANT app_user TO school_os_app';
            END IF;
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'school_os_migrator') THEN
                EXECUTE 'GRANT app_migrator TO school_os_migrator';
            END IF;
        END $$;
        """
    )

    # Migrations create tables owned by the migrator role. Grant default table
    # privileges to app_user so every future table is usable by the app without
    # a per-table GRANT. Default privileges are per-database; this runs in the
    # database being migrated.
    op.execute(
        """
        DO $$
        BEGIN
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT USAGE, SELECT ON SEQUENCES TO app_user;
        EXCEPTION WHEN insufficient_privilege THEN
            NULL;  -- ops has already configured this; nothing to do.
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'school_os_migrator') THEN
                EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE school_os_migrator IN SCHEMA public '
                        || 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user';
                EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE school_os_migrator IN SCHEMA public '
                        || 'GRANT USAGE, SELECT ON SEQUENCES TO app_user';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Roles and their memberships are managed out-of-band; we only unwind the
    # default privileges this migration introduced.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM app_user"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'school_os_migrator') THEN
                EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE school_os_migrator IN SCHEMA public '
                        || 'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user';
                EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE school_os_migrator IN SCHEMA public '
                        || 'REVOKE USAGE, SELECT ON SEQUENCES FROM app_user';
            END IF;
        END $$;
        """
    )