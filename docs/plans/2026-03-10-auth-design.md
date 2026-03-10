# Auth & User Management Design

## Context

AdForge is a demo tool for potential clients. Currently it has a single shared `ADFORGE_API_KEY` env var, only the brands router is protected, and there are no user/API key database models. We need multi-user isolation so each demo client gets their own API key and sees only their own data.

## Decision: API Key as Token

Each user gets a hashed API key stored in the database. The API key itself is the Bearer token — no JWT, no sessions. The existing frontend flow (paste key → store in cookie → send as Bearer) stays the same.

Rejected alternatives:
- **API Key → JWT exchange:** Short-lived JWTs with refresh flow. Overkill for a demo tool.
- **Session-based auth:** Server-side sessions with HttpOnly cookies. Requires session store, CSRF protection, doesn't match existing Bearer pattern.

## Database Models

### `users` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK, auto-generated |
| `name` | VARCHAR(255) | Display name (e.g. "Acme Corp Demo") |
| `is_admin` | BOOLEAN | Default false. Admin bypasses data scoping. |
| `created_at` | TIMESTAMPTZ | Auto |

### `api_keys` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users.id, CASCADE |
| `key_hash` | VARCHAR(64) | SHA-256 of the full key |
| `key_prefix` | VARCHAR(8) | First 8 chars, for display/identification |
| `expires_at` | TIMESTAMPTZ | created_at + 14 days |
| `is_active` | BOOLEAN | Default true, for manual revocation |
| `created_at` | TIMESTAMPTZ | Auto |

### `brands` table change

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | UUID | FK → users.id, nullable initially for migration, then NOT NULL |

Key format: `adf_<32 random hex chars>`. Only the SHA-256 hash is stored. The plaintext key is shown once at creation.

## Data Scoping

Ownership cascades through brand: User → Brand → (Products, Audiences, Jobs → (Steps, Outputs → PerformanceMetrics, Events)).

- Brand queries add `.where(Brand.user_id == user.id)`
- Job/output/performance queries join through Brand to filter by user
- Admin users (`is_admin=True`) bypass scoping and see everything

## Auth Flow

### `require_auth` dependency (replaces current)

1. Extract Bearer token from `Authorization` header
2. SHA-256 hash the token
3. Look up `api_keys` by `key_hash` where `is_active = true` and `expires_at > now()`
4. If not found → 401
5. Eager-load the associated `User`
6. Return the `User` object

### `POST /api/auth/validate` (replaces current)

- Accepts `{api_key: string}`, hashes it, looks it up same way
- Returns `{valid: true, user_name: string}` on success
- Frontend stores plaintext key in cookie, sends as Bearer — same as today

### Route protection

All routers get `Depends(require_auth)`: brands (already has it), jobs, outputs, performance, deployment.

## CLI Tool

Script at `backend/app/cli.py`, invoked via `python -m app.cli`:

```
python -m app.cli create-user "Acme Corp Demo" [--admin] [--expires-days 14]
```
Creates user + API key. Copies seed data (GlowVita) with new UUIDs assigned to the new user. Prints plaintext key once.

```
python -m app.cli list-users
```
Table: name, key prefix, expires_at, is_active, brand count.

```
python -m app.cli revoke-key <key_prefix>
```
Sets `is_active = false` on the matching key.

```
python -m app.cli delete-user <user_id>
```
Cascades: deletes user → api_keys → brands → jobs → outputs etc.

## Frontend Changes

### Next.js middleware (new: `frontend/src/middleware.ts`)
- Checks for `adforge_api_key` cookie on all `/(dashboard)` routes
- Missing cookie → redirect to `/login`

### API client 401 handling
- On 401 response: clear cookie, redirect to `/login`

### Logout button
- In the sidebar: clears cookie, redirects to `/login`

### No other UI changes
Login page stays the same. No user profile, no key management UI.

## Migration Strategy

Alembic migration:

1. Create `users` and `api_keys` tables
2. Add `brands.user_id` as nullable
3. Data migration: create default admin user, assign all existing brands to it, generate admin API key
4. Alter `brands.user_id` to NOT NULL

The `ADFORGE_API_KEY` env var and `adforge_api_key` config setting are removed. All keys live in the database.

## Removed

- `ADFORGE_API_KEY` env var
- `settings.adforge_api_key` config field
- Static key comparison in `require_auth` and `/api/auth/validate`
