# Phase 1: School OS API — Backend Implementation Plan (Revised)

## Context

We are building the `school-os-api` FastAPI backend from scratch. The PRD (4,053 lines) and ARCHITECTURE doc are the authoritative sources. The directory is currently empty. This plan covers the Phase 1 foundation only — the load-bearing parts that every future module inherits. Future modules (students, attendance, fees, AI, etc.) must be additions, not rewrites.

The ARCHITECTURE doc has made expensive decisions we will follow. Where it is silent, this plan fills gaps with current production best practices.

---

## Final Architecture: Modular Monolith

One deployable FastAPI application with clear domain boundaries. No microservices. Modules communicate via service interfaces or the outbox event table — never by importing another module's repository.

**Why not microservices:** Tier-2/3 Indian schools at 200–2,000 students cannot absorb the operational cost of distributed systems. The modular structure allows extracting specific modules (notifications, AI) later if scale demands it, without rewriting the remaining system.

---

## Technology Stack (Pinned Decisions)

| Concern | Choice | Version | Reason |
|---|---|---|---|
| Framework | FastAPI | 0.115.x | Async-native, built-in OpenAPI, Python type system |
| Validation | Pydantic v2 | 2.7.x | Native FastAPI integration, strict mode, fast |
| ORM | SQLAlchemy | 2.0.x (async) | Declarative models, `version_id_col`, async-first |
| Migrations | Alembic | 1.13.x | Industry standard, deterministic, reversible |
| DB driver | asyncpg | 0.29.x | Fastest async PostgreSQL driver; no psycopg2 |
| Config | pydantic-settings | 2.1.x | Type-safe env var loading |
| Password hashing | argon2-cffi | 23.1.x | Argon2id — memory-hard, OWASP/NIST recommended for new systems. NOT passlib/bcrypt. |
| JWT | PyJWT | 2.8.x | Actively maintained. NOT python-jose (sporadic maintenance) |
| Logging | structlog | 24.x | Structured JSON, request ID binding |
| ASGI server | uvicorn | 0.27.x | Production ASGI |
| Testing | pytest + pytest-asyncio + httpx | 0.23.x | Async-compatible |
| Database | PostgreSQL | 16+ | RLS, JSONB, constraints |

**Argon2 directly, not passlib:**
```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=4)
ph.hash(password)          # hash
ph.verify(stored, given)   # verify; raises if wrong
ph.check_needs_rehash(h)   # upgrade old hashes
```

---

## Project Structure

```
school-os-api/
├── alembic/
│   ├── versions/
│   │   ├── 0001_db_roles_and_rls_setup.py    ← creates app_user, app_migrator roles
│   │   └── 0002_iam_core.py                  ← organizations, schools, users, memberships, roles
│   └── env.py              ← imports all models; runs as app_migrator (BYPASSRLS)
│
├── app/
│   ├── main.py             ← FastAPI app factory + lifespan
│   ├── core/
│   │   ├── config.py       ← pydantic-settings (reads .env)
│   │   ├── errors.py       ← error codes, exception classes, handlers
│   │   ├── context.py      ← RequestContext dataclass (user, school_id, request_id)
│   │   ├── security.py     ← JWT encode/decode, token utilities (PyJWT)
│   │   ├── hashing.py      ← argon2-cffi PasswordHasher wrapper
│   │   ├── permissions.py  ← Permission registry, DataScope enum
│   │   ├── authz.py        ← require() guard, scope resolution
│   │   ├── pagination.py   ← CursorPage, OffsetPage, params
│   │   └── logging.py      ← structlog setup
│   │
│   ├── db/
│   │   ├── base.py         ← SQLAlchemy declarative Base
│   │   ├── mixins.py       ← TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
│   │   ├── session.py      ← async engine, async_sessionmaker, get_db dependency
│   │   ├── rls.py          ← set_tenant_context(session, school_id) helper
│   │   └── types.py        ← ULIDType (custom SQLAlchemy type), UTCDateTime
│   │
│   ├── modules/
│   │   ├── iam/
│   │   │   ├── organizations/
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py      ← Pydantic request/response (never raw ORM)
│   │   │   │   ├── repository.py   ← explicit SQL, no magic
│   │   │   │   ├── service.py      ← business rules
│   │   │   │   ├── router.py
│   │   │   │   └── permissions.py  ← ORG_READ, ORG_CREATE, etc.
│   │   │   ├── schools/            ← same structure
│   │   │   ├── users/              ← same structure
│   │   │   ├── memberships/        ← same structure
│   │   │   └── roles/              ← system roles, permission sync
│   │   │
│   │   ├── auth/
│   │   │   ├── models.py   ← RefreshToken, LoginAttempt
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py   ← /auth/* endpoints
│   │   │
│   │   ├── people/
│   │   │   ├── persons/    ← org-scoped shared identity
│   │   │   ├── addresses/  ← reusable address model
│   │   │   └── contacts/   ← phone/email, primary/emergency flags
│   │   │
│   │   └── platform_/
│   │       ├── audit/      ← AuditLog model + audit() helper
│   │       └── outbox/     ← OutboxEvent table only (no worker in Phase 1)
│   │
│   └── api/
│       └── v1/
│           └── router.py   ← aggregates module routers (only file touched when adding a module)
│
├── tests/
│   ├── conftest.py         ← fixtures: async session, test client, seed data
│   ├── unit/
│   │   ├── test_authz.py
│   │   ├── test_pagination.py
│   │   ├── test_hashing.py
│   │   └── test_jwt.py
│   └── integration/
│       ├── test_rls_coverage.py      ← structural: queries pg_class
│       ├── test_tenant_isolation.py  ← School A cannot see School B
│       ├── test_auth.py
│       └── test_iam.py
│
├── scripts/
│   └── sync_permissions.py  ← syncs code-declared permissions → DB
│
├── .env.example
├── pyproject.toml
├── alembic.ini
├── Makefile
└── docker-compose.yml       ← postgres only for local dev
```

**Adding a future module touches exactly two shared files:**
- One `include_router(...)` line in `api/v1/router.py`
- One `import` in `alembic/env.py`
Nothing in IAM, middleware, or the app factory.

---

## AsyncSession Lifecycle and Transaction Handling

### Correct Pattern

```python
# db/session.py
engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://...
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # prevents post-commit lazy-load errors in async
    autoflush=False,          # explicit flushes only; prevents accidental queries
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        async with session.begin():  # single transaction per request
            yield session
            # commits on clean exit; rolls back on exception
```

**Why `session.begin()` wraps the yield:**
- Ensures every request runs in an explicit transaction (required for `SET LOCAL`)
- `SET LOCAL` only takes effect inside a `BEGIN`/`COMMIT` block — it is silently ignored outside a transaction
- Auto-commits on success, auto-rolls-back on exception
- Each request gets a fresh session from the pool; no state leakage

**Why `expire_on_commit=False`:** In async SQLAlchemy, accessing expired attributes after commit triggers a lazy load, which raises `MissingGreenlet`. Disabling expiry means loaded attributes remain accessible after commit.

**Repository methods do not commit.** Only the `get_db` dependency manages the transaction boundary. Services call repositories; the request lifecycle commits.

---

## PostgreSQL RLS Design

### Database Roles (two roles, not one)

```sql
-- Migration 0001 creates these:
CREATE ROLE app_user NOLOGIN;          -- application role; RLS enforced
CREATE ROLE app_migrator NOLOGIN BYPASSRLS;  -- migrations; DDL without RLS interference

-- Application connects as: app_user (enforced)
-- Alembic connects as: app_migrator (bypasses RLS for schema changes)
-- Superuser is NEVER used in the app connection string
```

**Why two roles:**
- `SUPERUSER` and `BYPASSRLS` roles skip all RLS policies. If the app connects as superuser, RLS provides zero protection.
- Alembic needs `BYPASSRLS` so it can modify tables without triggering tenant policies during migrations.
- The app connection must be `app_user` — no escape hatch.

### SET LOCAL Pattern (connection-pooling safe)

```python
# db/rls.py
async def set_tenant_context(session: AsyncSession, school_id: UUID | None) -> None:
    """
    Set the RLS context for the current transaction.
    Must be called AFTER session.begin() — SET LOCAL is transaction-scoped.
    With pgBouncer or SQLAlchemy pooling, SET LOCAL is safe because it
    resets when the transaction ends. SET (without LOCAL) persists on the
    connection and is DANGEROUS with pooling.
    """
    if school_id is not None:
        await session.execute(
            text("SET LOCAL app.current_school_id = :sid"),
            {"sid": str(school_id)},
        )
    else:
        await session.execute(text("SET LOCAL app.current_school_id = ''"))
```

```sql
-- RLS policy (migration 0001)
ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE schools FORCE ROW LEVEL SECURITY;

CREATE POLICY school_isolation ON schools
  AS RESTRICTIVE
  TO app_user
  USING (
    id::text = current_setting('app.current_school_id', true)
    OR current_setting('app.current_school_id', true) = ''
  );
```

The `true` second argument to `current_setting` makes it return `''` (empty string) rather than raise an error when the variable is unset — important for requests that do not need school context (org-level operations).

### When set_tenant_context is called

The tenant middleware calls `set_tenant_context` immediately after `session.begin()` in `get_db`. This is done inside the FastAPI dependency, not in middleware, because middleware does not have access to the database session.

```
Request → AuthMiddleware (validates JWT) → Route Handler
  → get_db() creates session + begins transaction
  → get_context() reads X-School-ID, validates membership, calls set_tenant_context()
  → service/repository executes under RLS
```

### X-School-ID: Context Selector Only

`X-School-ID` is **not** an authorization mechanism. It is a context selector that tells the server which school's operational context to use for this request.

Authorization comes from the membership check:
```python
async def get_context(
    school_id_header: str | None = Header(None, alias="X-School-ID"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RequestContext:
    if school_id_header is None:
        # Some endpoints are org-level and don't need a school context
        return RequestContext(user=user, school_id=None, ...)
    
    school_id = UUID(school_id_header)  # 400 if malformed
    
    # THIS is the authorization check — not the header itself
    membership = await membership_repo.get_active(
        session, user_id=user.id, school_id=school_id
    )
    if membership is None:
        raise Forbidden("You do not have access to this school.")
    
    await set_tenant_context(session, school_id)  # now safe to set RLS
    return RequestContext(user=user, school_id=school_id, roles=membership.roles, ...)
```

A user who sends `X-School-ID: <school_they_dont_belong_to>` gets `403` — the header value is meaningless without a valid membership. The backend never trusts the header for access control.

---

## Authentication & Authorization

### Authentication Flow

```
POST /api/v1/auth/login
  → validate credentials (argon2-cffi verify)
  → record attempt; increment failure counter
  → if locked: 429 (uniform response, no enumeration)
  → if success: reset counter
  → issue access_token (JWT, 15 min) + refresh_token (opaque, 30 days)
  → store SHA-256(refresh_token) in refresh_tokens table

POST /api/v1/auth/refresh
  → hash the presented token; look up by digest
  → if not found or revoked: 401 (possible theft)
  → if already rotated (reuse of old token): revoke entire session family → 401
  → issue new pair; mark old token rotated

POST /api/v1/auth/logout
  → revoke session family

POST /api/v1/auth/password-reset/request  (rate-limited, always 200)
POST /api/v1/auth/password-reset/confirm
```

**JWT payload (minimal):**
```json
{ "sub": "<user_id>", "jti": "<token_id>", "exp": 1234567890 }
```
No roles, permissions, or school IDs in the token. Permissions resolved server-side on every request. Revoking a membership takes effect on the next request — no need to wait for token expiry.

**Uniform failure responses:** Wrong password, unknown email, disabled account, locked account — all return identical response body and near-identical timing (argon2-cffi's verify call provides natural constant time; no sleep needed).

### Authorization Design

```python
# core/permissions.py
class DataScope(str, Enum):
    OWN = "OWN"
    ASSIGNED = "ASSIGNED"
    SCHOOL = "SCHOOL"
    ORGANIZATION = "ORGANIZATION"
    PLATFORM = "PLATFORM"

    def strength(self) -> int:
        return ["OWN", "ASSIGNED", "SCHOOL", "ORGANIZATION", "PLATFORM"].index(self.value)

@dataclass
class Permission:
    code: str        # e.g. "students.student.read"
    module: str
    resource: str
    action: str
    description: str

class PermissionRegistry:
    _registry: dict[str, Permission] = {}

    def register(self, module, resource, action, description) -> Permission:
        code = f"{module}.{resource}.{action}"
        perm = Permission(code=code, ...)
        self._registry[code] = perm
        return perm

    def validate_all(self):
        """Called at app startup. Any require(UNKNOWN_CODE) crashes the process."""
```

```python
# modules/students/permissions.py (future module — shown for pattern clarity)
from app.core.permissions import registry, Action
STUDENT_READ = registry.register("students", "student", "read", "View students")
```

```python
# core/authz.py
def require(ctx: RequestContext, permission: Permission, scope: DataScope | None = None):
    """
    Checks that the current principal holds this permission.
    Scope resolution: when a user has multiple roles, strongest scope wins.
    OWN < ASSIGNED < SCHOOL < ORGANIZATION < PLATFORM
    Raises HTTP 403 if check fails.
    """
    effective_scope = ctx.effective_scope_for(permission.code)
    if effective_scope is None:
        raise Forbidden(f"Missing permission: {permission.code}")
    if scope and effective_scope.strength() < scope.strength():
        raise Forbidden(f"Insufficient scope for: {permission.code}")
```

**`require()` validates permission codes at import time** — if a route file references an unregistered code, the app fails to start. Typos are caught in CI, not in production.

---

## Repository Design (Explicit, Not Magic)

Avoid opaque base-class tenant-filter injection. Keep repositories explicit and readable.

```python
# modules/iam/schools/repository.py
class SchoolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, school_id: UUID, org_id: UUID) -> School | None:
        # org_id explicitly passed; never inferred from magic
        stmt = (
            select(School)
            .where(School.id == school_id, School.organization_id == org_id)
            .where(School.archived_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(self, org_id: UUID, *, page: CursorParams) -> CursorPage[School]:
        stmt = (
            select(School)
            .where(School.organization_id == org_id)
            .where(School.archived_at.is_(None))
            .order_by(School.created_at.desc(), School.id.desc())
        )
        return await paginate_cursor(self.session, stmt, page)
```

RLS provides defense-in-depth. The repository makes tenant filters **visible in the code** — another developer reading this knows exactly what scope is being applied. No hidden magic.

When a service needs a repository, it receives the session via dependency injection and constructs the repository explicitly:

```python
# modules/iam/schools/service.py
class SchoolService:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self.repo = SchoolRepository(session)
        self.ctx = ctx
```

---

## Database Entities (Phase 1)

### Entity Conventions

- **Primary keys:** ULIDs stored as `CHAR(26)` or `TEXT` with a custom SQLAlchemy type. Sortable, URL-safe, no UUID collision risk. Alternative: `UUID` — choose one, apply consistently.
- **Timestamps:** `TIMESTAMPTZ` (with time zone) in PostgreSQL. Always UTC. `created_at` and `updated_at` set by DB triggers or SQLAlchemy server defaults.
- **Date-only fields** (DOB, academic dates, attendance date): `DATE` type, not `TIMESTAMP`.
- **Status/enum fields:** `VARCHAR` + `CHECK` constraint from a Python enum. Not PostgreSQL native enums (hard to alter; `ALTER TYPE ... ADD VALUE` cannot be done in a transaction in older PG).
- **Soft deletes:** `archived_at TIMESTAMPTZ` for records that must survive for history (schools, persons, sections). `deleted_at TIMESTAMPTZ` reserved only for retention-policy removal of operationally safe data. Default queries filter `archived_at IS NULL`.

### TimestampMixin

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
```

### VersionMixin (Optimistic Locking)

```python
class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
```

Any `UPDATE` carries `WHERE version = :expected`. Stale write → SQLAlchemy raises `StaleDataError` → service catches → 409 `STALE_RESOURCE` with user-friendly message:
> "Someone else updated this record while you were editing. Refresh and reapply your changes."

### Core Tables

**RLS-enabled tables** (have `organization_id` or `school_id`; policies enforced):

```
organizations       id, name, code, plan_code, status, settings, parent_organization_id
schools             id, organization_id, name, code, status, timezone, address, settings, parent_school_id, hierarchy_path
users               id, email, password_hash, status, last_login_at, failed_login_attempts, locked_until, permissions_version
persons             id, organization_id, first_name, last_name, dob, gender, primary_phone, primary_email, photo_key, status, merged_into_person_id
addresses           id, entity_type, entity_id, organization_id, [address fields], is_primary
contacts            id, entity_type, entity_id, organization_id, type, value, is_primary, is_emergency
memberships         id, user_id, organization_id, school_id [nullable], status, valid_from, valid_until
roles               id, organization_id [NULL=system], name, code, is_system, description
membership_roles    membership_id, role_id, data_scope
permissions         id, code, module, resource, action, description
role_permissions    role_id, permission_id, data_scope
```

**RLS-exempt tables** (nullable `school_id`; access enforced at service/API layer only):

```
refresh_tokens      id, user_id, token_digest, session_family_id, expires_at, rotated_at, revoked_at, user_agent, ip_address
login_attempts      id, user_id [nullable], email_attempted, ip_address, success, attempted_at
audit_logs          id, organization_id [nullable], school_id [nullable], actor_id, action, entity_type, entity_id, before_snapshot [JSONB], after_snapshot [JSONB], request_id, ip_address, created_at
outbox_events       id, event_name, version, payload [JSONB], organization_id [nullable], school_id [nullable], status, attempts, last_attempted_at, error, created_at
```

RLS-exempt table allowlist is **explicitly asserted in `test_rls_coverage.py`**. Adding a new table to the allowlist requires deliberate code review — if you forget, the structural test fails CI.

---

## What Goes in Phase 1 (and What Stays Simple)

### In Phase 1: Yes

| Component | Scope |
|---|---|
| Audit log | Table + `audit()` helper function. Write in same transaction as domain change. |
| Outbox events | Table only. No worker, no dispatcher. Outbox row written atomically with domain change. A simple polling script or cron can read it later. |
| Feature flags | Table only. No middleware enforcement, no SDK. Just rows. |
| Background jobs | Table only. No worker. Jobs tracked manually or via simple queries. |

### In Phase 1: No (explicitly deferred)

| Component | Reason |
|---|---|
| Idempotency keys | Needed for attendance submission (Milestone 5). Add then. |
| Outbox dispatcher/worker | Add when first async notification is needed (Milestone 5). |
| Redis / permission caching | `users.permissions_version` column reserved; implement in Milestone 7. |
| Celery / ARQ | Not needed until background jobs require parallelism. |
| Search / full-text | Add in Milestone 6. |
| CSV export / reporting | Add in Milestone 6. |
| Student/Parent/Teacher profiles | Milestone 4. |
| Academic Year/Class/Section | Milestone 3. |
| All operational modules | Milestones 5+. |

---

## API Conventions

### Base URL: `/api/v1`

### Naming
- Resources are plural nouns: `/schools`, `/users`, `/memberships`
- Nested for ownership: `GET /organizations/{org_id}/schools`
- Flat for direct access: `GET /schools/{school_id}`

### Methods
- `POST` → create (201)
- `GET` → read (200)
- `PATCH` → partial update (200); never `PUT` for partial updates
- `DELETE` → soft delete / archive (200 or 204)

### Request/Response Conventions
- IDs always as strings in JSON (ULID is already a string)
- Timestamps: `"2024-01-15T10:30:00Z"` (UTC ISO 8601)
- Dates: `"2024-01-15"` (ISO 8601 date-only, no time component)
- Paginated lists always in a wrapper, never raw arrays
- Never return raw ORM objects — always Pydantic response schemas

### Pagination

```python
# Cursor (default) — stable under concurrent inserts
class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None
    has_more: bool

# Offset (opt-in, capped at 10,000 rows)
class OffsetPage[T](BaseModel):
    items: list[T]
    total: int | None   # None means not computed (expensive COUNT(*))
    page: int
    page_size: int
```

Sort fields are whitelist-validated — unknown sort field → 400, never SQL passthrough.

### Error Format

```json
{
  "error": {
    "code": "SCHOOL_NOT_FOUND",
    "message": "The requested school was not found.",
    "details": {},
    "request_id": "01J4X..."
  }
}
```

No stack traces in responses. Internal errors logged with full context. `request_id` links to logs.

**Common error codes:** `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `CONFLICT`, `STALE_RESOURCE`, `RATE_LIMITED`, `INTERNAL_ERROR`.

### Versioning

`/api/v1` is the current version. Breaking changes get `/api/v2`. Deprecations announced via `Deprecation` response header + sunset date. Old version remains live until migration window closes.

---

## Audit Logging

Audit writes happen in the **same transaction** as the domain change — audit is never a fire-and-forget:

```python
# platform_/audit/service.py
async def audit(
    session: AsyncSession,
    ctx: RequestContext,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    log = AuditLog(
        organization_id=ctx.organization_id,
        school_id=ctx.school_id,
        actor_id=ctx.user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_snapshot=before,
        after_snapshot=after,
        request_id=ctx.request_id,
    )
    session.add(log)
    # No commit here — part of caller's transaction
```

**What gets audited in Phase 1:** Login, logout, password change, org create/update, school create/update/suspend, user create/update/disable, membership create/update, role assignment.

**What is never logged:** Passwords, tokens, raw secrets, bulk read operations (list endpoints).

---

## Observability

### Structured Logging (structlog)

Every log line is JSON with at minimum:
```json
{
  "event": "...",
  "request_id": "...",
  "user_id": "...",
  "school_id": "...",
  "level": "info",
  "timestamp": "...",
  "endpoint": "GET /api/v1/schools/...",
  "status_code": 200,
  "duration_ms": 42
}
```

Request ID generated at intake (UUID v4), bound to structlog context for the request lifetime, returned in response headers and error bodies.

### Health Endpoints

```
GET /api/v1/health   → 200 {"status": "ok"}
GET /api/v1/ready    → 200 {"status": "ok", "db": "ok"}
                    or 503 {"status": "degraded", "db": "error: ..."}
```

`/ready` performs an actual DB query (`SELECT 1`). Used by load balancers and orchestrators.

---

## Testing Strategy

### Structural Rules

- Unit tests: No database. Run in < 5 seconds.
- Integration tests: Require `TEST_DATABASE_URL`. Run against a real PostgreSQL with RLS policies applied.
- Never mock the database in integration tests — the entire point of integration tests is to verify RLS policies, tenant isolation, and constraint enforcement.

### Unit Tests (no DB)

- `test_authz.py`: `require()` passes with correct permission, raises with missing/wrong-scope
- `test_pagination.py`: Cursor encoding, decoding, edge cases
- `test_hashing.py`: Hash/verify/check_needs_rehash lifecycle
- `test_jwt.py`: Encode/decode, expiry, tampered token detection
- `test_errors.py`: Exception → response shape for each error type
- `test_permissions.py`: Registry uniqueness, code format validation

### Integration Tests (real DB)

**`test_rls_coverage.py` (structural, not functional):**
```python
async def test_every_tenant_table_has_rls_policy(db):
    """
    Query pg_class + pg_policy.
    Any table with a 'school_id' or 'organization_id' column must have an RLS policy
    OR be in the explicit allowlist (audit_logs, outbox_events, etc.).
    Fails CI if a developer adds a tenant table and forgets the policy.
    Adding to the allowlist requires deliberate code review.
    """
```

**`test_tenant_isolation.py`:**
```python
async def test_school_a_user_cannot_read_school_b_data(client, school_a_token, school_b):
    response = await client.get(
        f"/api/v1/schools/{school_b.id}",
        headers={"Authorization": f"Bearer {school_a_token}",
                 "X-School-ID": str(school_b.id)},
    )
    assert response.status_code == 403  # membership check fails before RLS

async def test_rls_blocks_direct_school_b_query(db_session_as_school_a, school_b):
    # Bypass middleware; call repository directly with school_a's tenant context
    # Verify RLS returns zero rows for school_b resources
```

**`test_auth.py`:** Login success/failure, uniform error timing, lockout, refresh rotation, family revocation on reuse.

**`test_iam.py`:** Org CRUD, school CRUD, membership creation, role assignment.

**`test_tenant_context_isolation.py`:** `SET LOCAL` is transaction-scoped; a new transaction on the same connection starts with no tenant context.

### Seed Fixtures

- 2 organizations, 2 schools each
- 1 user per role type (ORG_ADMIN, SCHOOL_ADMIN, TEACHER, PARENT, STUDENT)
- Users with overlapping school memberships
- Disabled/suspended users
- System roles pre-seeded

---

## Security

### Threat Model (Phase 1 relevant)

| Threat | Mitigation |
|---|---|
| Cross-tenant data access (IDOR) | Membership check on every request; RLS as backup; `test_tenant_isolation` |
| Account enumeration | Uniform login responses; argon2 verify provides natural timing |
| Token theft | Refresh token rotation + family revocation; SHA-256 digest storage |
| JWT tampering | `PyJWT` signature verification; HS256 with secret from env |
| Privilege escalation | `require()` on every route; scopes enforced in `get_context` |
| Unsafe sort/filter passthrough | Whitelist-validated sort fields; parameterized queries only |
| Secrets in source | All secrets via env vars/pydantic-settings; never in git |
| Missing RLS policy | Structural test fails CI |
| Connection pool tenant leak | `SET LOCAL` (transaction-scoped); tested in `test_tenant_context_isolation` |

### Rate Limiting (Phase 1)

Apply rate limits at the route level using a simple in-process counter (or nginx/reverse proxy):
- `POST /auth/login`: 5 attempts per IP per minute
- `POST /auth/password-reset/request`: 3 per IP per hour

Production: move to Redis-backed rate limiting (Milestone 7).

### Input Validation

Pydantic v2 strict mode on all request models. No raw string passthrough to queries. All SQL via SQLAlchemy parameterized statements — no `text()` with f-strings.

---

## Migrations Strategy

```
alembic/versions/
  0001_db_roles_and_rls.py      ← CREATE ROLE app_user, app_migrator; RLS setup; SET LOCAL function
  0002_iam_core.py              ← organizations, schools, users, memberships, roles, permissions tables
  0003_auth_tables.py           ← refresh_tokens, login_attempts
  0004_people_foundation.py     ← persons, addresses, contacts
  0005_platform_tables.py       ← audit_logs, outbox_events, feature_flags, background_jobs
```

Rules:
- Alembic runs as `app_migrator` (BYPASSRLS) — never `app_user`
- Migrations are deterministic, reversible (downgrade implemented), and tested in staging before production
- No manual DDL on production database
- New tenant tables without RLS policies fail the `test_rls_coverage` CI check

---

## Implementation Milestones (Phase 1)

### Milestone 1 — Foundation (Estimated: 3–4 days)

1. `pyproject.toml` with all dependencies; `Makefile` with dev shortcuts
2. `app/core/config.py`: all env vars typed with pydantic-settings
3. `app/core/logging.py`: structlog JSON, request ID binding
4. `app/core/errors.py`: error code enum, exception hierarchy, FastAPI handlers
5. `app/core/context.py`: `RequestContext` dataclass, skeleton `get_context` dependency
6. `app/db/base.py`, `mixins.py` (Timestamp, Actor, Version, SoftDelete)
7. `app/db/session.py`: engine, `async_sessionmaker`, `get_db` with `session.begin()`
8. `app/db/types.py`: ULID type, UTCDateTime
9. `app/core/pagination.py`: `CursorPage`, `OffsetPage`, cursor encode/decode
10. `app/main.py`: app factory, lifespan (DB ping), middleware registration
11. `GET /api/v1/health`, `GET /api/v1/ready`
12. Alembic init + `env.py` (imports all models for autogenerate; connects as `app_migrator`)
13. Migration 0001: `app_user`, `app_migrator` roles; `FORCE ROW LEVEL SECURITY` boilerplate
14. Unit tests: errors, pagination, config loading

**Milestone 1 is done when:** `make dev` starts the server; `/health` returns 200; `/ready` verifies DB connection; `make test-unit` passes.

### Milestone 2 — IAM & Multi-Tenancy (Estimated: 5–7 days)

1. `app/core/permissions.py`: `Permission`, `DataScope`, `PermissionRegistry`, startup validation
2. `app/core/authz.py`: `require()`, scope strength ordering, `get_context` fully implemented
3. `app/core/hashing.py`: argon2-cffi wrapper (`hash`, `verify`, `check_needs_rehash`)
4. `app/core/security.py`: PyJWT encode/decode, `get_current_user` dependency
5. `app/db/rls.py`: `set_tenant_context(session, school_id)`
6. Migration 0002: organizations, schools, users, memberships, roles, permissions, role_permissions
7. `modules/iam/organizations/`: model, schema, repo (explicit), service, router, permissions
8. `modules/iam/schools/`: same
9. `modules/iam/users/`: model, schema, service (no login yet)
10. `modules/iam/roles/`: system role seeder (SUPER_ADMIN, ORG_ADMIN, SCHOOL_ADMIN, PRINCIPAL, TEACHER, STAFF, PARENT, STUDENT)
11. `modules/iam/memberships/`: user → school → role(s)
12. Migration 0003: `refresh_tokens`, `login_attempts`
13. `modules/auth/`: login, refresh, logout, password-reset endpoints
14. `modules/platform_/audit/`: `AuditLog` model, `audit()` helper
15. Migration 0004: people tables (persons, addresses, contacts)
16. `modules/people/persons/`: model, schema, repo, service, router
17. Migration 0005: platform tables (audit_logs, outbox_events, feature_flags, background_jobs)
18. `scripts/sync_permissions.py`
19. Integration tests: RLS coverage structural test, tenant isolation, auth suite

**Milestone 2 is done when:** A user can register, login, be assigned to a school with a role, and call a permission-guarded endpoint. `test_rls_coverage` and `test_tenant_isolation` pass.

---

## Important Decisions and Trade-offs

| Decision | Chosen | Alternative Considered | Reason |
|---|---|---|---|
| ID format | ULID (26-char string) | UUIDv4 | Sortable by creation time; URL-safe; avoids UUID hotspot on B-tree indexes |
| Password hashing | Argon2id (argon2-cffi) | bcrypt (passlib) | Memory-hard; GPU-resistant; OWASP-recommended for new systems |
| JWT library | PyJWT | python-jose | python-jose maintenance is inconsistent; PyJWT is actively maintained |
| ORM | SQLAlchemy 2.0 async | Tortoise ORM, Django ORM | Mature, flexible, works with Alembic, sync-capable if needed |
| DB role separation | app_user + app_migrator | Single superuser | Superusers bypass RLS; two roles enforces the security model |
| SET LOCAL vs SET | SET LOCAL | SET | SET persists across pooled connections; SET LOCAL is transaction-scoped |
| Repository pattern | Explicit per-repository | Magic BaseRepository | Explicit is readable; magic obscures tenant scoping and is hard to audit |
| Outbox in Phase 1 | Table only, no worker | Skip entirely | Schema must be there from day 1 to write atomic events; worker can come later |
| VARCHAR + CHECK for enums | Yes | PostgreSQL native enum | Native enums need DDL to extend; VARCHAR + CHECK is one-line migration |
| Pagination default | Keyset cursor | Offset | Offset degrades on large datasets; cursor is stable under concurrent inserts |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SET LOCAL outside a transaction is silently ignored | Tenant context not applied; RLS uses empty string | `get_db` always wraps yield in `session.begin()`; integration test asserts RLS works |
| New developer adds tenant table without RLS policy | Silent data leakage | `test_rls_coverage.py` fails CI automatically |
| Refresh token reuse (session theft) | Account takeover | Family revocation on reuse; SHA-256 digest storage |
| Stale write overwrites concurrent edit | Data loss | `VersionMixin`; 409 `STALE_RESOURCE` on mismatch |
| Audit write fails silently | Compliance gap | Audit in same transaction as domain change; no fire-and-forget |
| X-School-ID treated as authorization | IDOR attack surface | Header is context selector only; membership check is the auth gate |
| Module boundaries violated | Cross-domain coupling | Each module imports only from `core/` and `db/`; never another module's repo |
| Permission typo silently passes | Unauthorized access goes unchecked | Registry validates all codes at startup; typo = process fails to start |
| app_migrator credentials in app config | RLS bypass in production | Separate env vars for app connection vs migration connection; CI uses migration creds; production app uses app_user only |

---

## PRD Ambiguities Needing Resolution Before Implementation

### Must Decide Before Phase 1

1. **ULID vs UUID:** Pick one. Plan recommends ULID. Confirm before migration 0001.

2. **`app_user` password and connection string:** Decide whether `app_user` is a role or a login role. In PostgreSQL, `NOLOGIN` roles cannot own a connection string. You need a login role (e.g., `school_os_app`) that inherits `app_user` privileges. Alembic needs a separate login role (`school_os_migrator`) with `BYPASSRLS`.

3. **Org-level vs school-level operations without `X-School-ID`:** Which endpoints are org-scoped (no school header required)? Recommendation: document the rule — if an endpoint reads/writes a specific school's data, `X-School-ID` is required. If it operates across the org (listing schools, org settings), it is optional.

### Safe to Defer

4. Overlapping academic year configuration rules (Milestone 3)
5. Bulk import atomicity policy per domain (Milestone 4+)
6. Permission cache TTL / Redis strategy (Milestone 7; column reserved)
7. Cross-school org-level reporting API design (Milestone 6)
8. Notification preferences schema (Milestone 5)

---

## Verification

```bash
make dev           # starts fastapi dev server
make test-unit     # no DB; runs in < 5s
make test-int      # requires TEST_DATABASE_URL; includes RLS + isolation tests
make migrate       # runs alembic upgrade head; verifies no drift
make sync-perms    # syncs permission registry → DB

# Manual checks:
# 1. Login, get token, call protected endpoint → 200
# 2. Use School A token with X-School-ID of School B → 403
# 3. Tamper JWT signature → 401
# 4. Exhaust refresh token rotation (reuse old token) → 401, session revoked
# 5. Call endpoint referencing unregistered permission code → server fails to start
```
