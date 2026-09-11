# School OS API

Multi-tenant School Management System backend. Phase 1 delivers the load-bearing
foundation: modular-monolith FastAPI service, identity + access management, and
PostgreSQL row-level security.

See the workspace root `ARCHITECTURE.md` and `implementation_plan.md` for the
design decisions and rationale.

## Quick start

```bash
make install              # creates .venv and installs dependencies
cp .env.example .env      # then set a real SECRET_KEY
docker compose up -d      # PostgreSQL 16 with dev roles
make migrate              # alembic upgrade head
make sync-perms           # sync code-declared permissions -> DB
make sync-roles           # seed system roles
make bootstrap            # create a demo org/school/admin
make dev                  # uvicorn on http://localhost:8000
```

API docs at `http://localhost:8000/docs`.

## Testing

```bash
make test-unit            # no database required
docker compose up -d      # database for integration tests
make migrate              # dev schema
export TEST_DATABASE_URL=postgresql+asyncpg://school_os_app:school_os_app_dev@localhost:5432/school_os_test
make test-int             # RLS + tenant isolation + auth + IAM
```

## Layout

```
app/
├── core/          config, errors, context, security, permissions, authz, pagination
├── db/            base + mixins, session, RLS, types, repository helpers
├── modules/       iam · people · auth · platform_ (audit, outbox)
├── api/v1/        router aggregation (only shared file touched per module)
alembic/           migrations, run as the BYPASSRLS migrator role
scripts/           sync-permissions · sync-roles · bootstrap · check-rls
tests/             unit (no DB) · integration (needs TEST_DATABASE_URL)
```

Adding a module touches exactly two shared files: one `include_router` line in
`app/api/v1/router.py` and one import in `alembic/env.py`.