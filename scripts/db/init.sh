#!/bin/bash
# Local-development database bootstrap. Runs once, on first container init,
# as the PostgreSQL superuser. Creates the RLS-enforced app login role and the
# BYPASSRLS migration role, then creates a dedicated test database.
#
# Production deployments create equivalent roles out-of-band; migration 0001
# re-declares them idempotently so this is purely a convenience layer.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    CREATE ROLE school_os_app LOGIN INHERIT PASSWORD 'school_os_app_dev';
    CREATE ROLE school_os_migrator LOGIN INHERIT BYPASSRLS CREATEROLE PASSWORD 'school_os_migrator_dev';
    CREATE DATABASE school_os_test OWNER postgres;
EOSQL

# Schema privileges per database. PostgreSQL 15+ restricts CREATE on `public`
# to the schema owner, so the migration role must be granted it explicitly.
for db in school_os school_os_test; do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        GRANT CREATE, USAGE ON SCHEMA public TO school_os_migrator;
        GRANT USAGE ON SCHEMA public TO school_os_app;
EOSQL
done

# The app role is a member of app_user; migration 0001 performs the grant
# whenever it is able, but doing it here (as superuser) makes it unconditional.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user NOLOGIN;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_migrator') THEN
            CREATE ROLE app_migrator NOLOGIN BYPASSRLS;
        END IF;
    END $$;
    GRANT app_user TO school_os_app;
    GRANT app_migrator TO school_os_migrator;
EOSQL