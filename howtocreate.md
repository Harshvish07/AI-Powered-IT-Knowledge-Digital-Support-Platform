# How This Was Built — Phase-by-Phase Log

This file is a running, dated build log: what was done in each phase, why, and any
non-obvious problems encountered and how they were solved. It complements
[`README.md`](./README.md) (usage) and [`PROJECT_INFO.md`](./PROJECT_INFO.md) (roadmap/context).

---

## Phase 1 — Project Foundation (2026-09-12)

### Goal

Stand up the full monorepo skeleton — frontend, backend, database, Docker, tooling, docs — with
a single working `GET /health` endpoint. No auth, tickets, RAG, or AI logic yet, by design.

### What was created

**Repository layout**

```
project-root/
  frontend/   (Next.js 16, TypeScript, Tailwind CSS 4)
  backend/    (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2)
  docs/       (architecture.md with Mermaid diagram)
  scripts/    (dev-backend.sh, migrate.sh)
  docker-compose.yml
  .env.example
  README.md, PROJECT_INFO.md, howtocreate.md
```

**Backend** (`backend/app/`)
- `main.py` — FastAPI app, CORS middleware, mounts the health router.
- `api/health.py` — `GET /health` → `{"status": "ok"}`.
- `core/config.py` — `Settings` (pydantic-settings) reads env vars / `.env`.
- `core/database.py` — SQLAlchemy engine, `SessionLocal`, declarative `Base`, `get_db()` dependency.
- `models/`, `schemas/`, `services/`, `repositories/`, `utils/`, `workers/` — empty (with
  `__init__.py`) package placeholders for future phases, matching the required architecture.
- `alembic/` — configured against `Settings.database_url`; first migration
  (`0001_enable_pgvector.py`) runs `CREATE EXTENSION IF NOT EXISTS vector`.
- `tests/test_health.py` — Pytest + FastAPI `TestClient` test for `/health`.
- Tooling: `ruff` (lint), `black` (format), `mypy` (types), configured in `pyproject.toml`.

**Frontend** (`frontend/`)
- Scaffolded with `create-next-app` (App Router, TypeScript, Tailwind, ESLint).
- Added the required folders: `components/`, `features/`, `hooks/`, `lib/`, `types/`, `tests/`.
- `app/page.tsx` — dashboard placeholder: a live backend-status card
  (`features/system-status/SystemStatusCard.tsx`, using `hooks/useHealthStatus.ts` to poll
  `GET /health`), plus "coming soon" cards for Knowledge Base / Tickets / AI Assistant / Auth —
  making it explicit in the UI that those are future phases, not missing bugs.
- `lib/config.ts` — reads `NEXT_PUBLIC_API_BASE_URL` for the backend URL.
- Playwright configured (`playwright.config.ts`, `tests/dashboard.spec.ts`) for e2e testing.
- Prettier configured for formatting (`.prettierrc.json`).

**Infrastructure**
- Root `docker-compose.yml` runs three services: `postgres` (`pgvector/pgvector:pg16`),
  `backend` (FastAPI via Uvicorn, hot reload), `frontend` (Next.js dev server). Bind-mounts
  source directories for live-reload dev; `postgres_data` named volume for persistence.
- `backend/Dockerfile`, `frontend/Dockerfile`.
- Root `.env.example` (Docker Compose variables) and `backend/.env.example` (standalone backend).
- `.gitignore` at root and per-project.

### Why these choices

See [`PROJECT_INFO.md`](./PROJECT_INFO.md) for the full tech-stack rationale table. Key
Phase-1-specific decisions:
- **pgvector via `pgvector/pgvector:pg16` image, enabled through an Alembic migration** (not a
  manual SQL step) — so enabling the extension is versioned, reproducible, and applies the same
  way in every environment.
- **`psycopg[binary]`** instead of plain `psycopg` — avoids needing a C compiler / `libpq-dev` in
  the backend image at all (see "Problems encountered" below).
- **Repositories/services split** in the backend from day one, even though both are currently
  near-empty — later phases (tickets, RAG) add real logic into these layers without a
  restructuring pass.

### Problems encountered & how they were resolved

These are documented because they're easy to hit again in later phases on this same machine/repo.

1. **`C:` drive had almost no free space (down to 0 bytes at one point).**
   This is a pre-existing condition of the machine, not caused by the project (all project files
   live on `D:`, which has ~100GB+ free). It broke, at different points: `npm install`
   (`ENOSPC`), `pip install` (`OSError: no space left on device`), and even Docker Desktop's own
   startup (its backend process wrote `There is not enough space on the disk` to its own log and
   silently got stuck in a broken, half-started state).
   - **Fix for npm**: redirected npm's global cache to `D:\npm-cache-tmp` and set the `TEMP`/`TMP`
     user environment variables to `D:\npm-tmp` (via `setx`, so it persists across shells).
   - **Fix for pip**: used `PIP_CACHE_DIR=D:\pip-cache-tmp` for backend dependency installs.
   - **Fix for the stuck Docker Desktop**: killing all `docker*`/`com.docker.backend` processes,
     running `wsl --shutdown`, and relaunching Docker Desktop fresh (a simple relaunch of the
     `.exe` while it's in that stuck state just refocuses the broken window — it does not
     actually restart the backend).
   - **Takeaway**: if Docker or npm/pip start behaving strangely on this machine again, check
     `df -h C:` first before debugging the tool itself.

2. **The project folder name contains `&`** (`...IT Knowledge & Digital Support Platform`),
   which broke Windows' default `cmd.exe`-based npm script shim — `npm run lint`, `npm run dev`,
   etc. all failed with `'Digital' is not recognized as an internal or external command`
   (cmd.exe treats unquoted `&` as a command separator). This also broke `create-next-app`'s own
   post-install `next typegen` step during scaffolding (non-fatal — dependencies still installed).
   - **Fix**: added `frontend/.npmrc` with `script-shell=C:/Program Files/Git/usr/bin/bash`,
     scoped to this project only (not a global npm config change) so it doesn't affect other
     projects on this machine.
   - **Side effect this caused**: because `docker-compose.yml` bind-mounts `./frontend:/app` for
     live-reload, that Windows-only `.npmrc` was also mounted straight into the Linux frontend
     container, where `C:/Program Files/Git/usr/bin/bash` doesn't exist — breaking `npm run dev`
     inside Docker with `spawn ... ENOENT`. Excluding `.npmrc` via `frontend/.dockerignore` only
     stops it from being baked into the *image*; it does nothing for the bind mount at runtime.
     The actual fix was overriding it back in the container environment: `docker-compose.yml`
     sets `npm_config_script_shell: /bin/sh` on the `frontend` service, which takes precedence
     over the mounted `.npmrc` file.
   - **Takeaway**: any future host-only workaround placed inside a directory that Compose
     bind-mounts into a container needs an explicit override (env var or otherwise) on the
     container side, or it will silently leak in.

3. **`gcc` + `libpq-dev` in `backend/Dockerfile` were unnecessary** and made the backend image
   build slow and disk-heavy (pulling in a full GCC toolchain, ~150MB+ of packages) right when
   disk space was already the tightest constraint. `psycopg[binary]` ships prebuilt wheels, so no
   compiler is needed. Removed the `apt-get install` step entirely — backend image build time
   dropped from ~2+ minutes (partway through, then it crashed) to ~35 seconds.

4. **Python 3.14 (the machine's default `py` interpreter) initially failed to install pinned
   dependency versions** (`pydantic-core` had no prebuilt wheel for that pin, and building from
   source needs a Rust toolchain that couldn't download either, due to problem #1). Re-resolved
   `requirements.txt`/`requirements-dev.txt` to the latest versions of each package (which do
   ship 3.14 wheels) and pinned to what was actually installed and tested. The `backend/Dockerfile`
   still targets `python:3.12-slim`, which has no trouble with these same pins.

### Verification performed

| Check | Result |
|---|---|
| `pytest` (backend, host venv) | ✅ 1 passed |
| `ruff check .` (backend) | ✅ all checks passed |
| `black --check .` (backend) | ✅ no changes needed |
| `mypy app` (backend) | ✅ no issues, 13 source files |
| `npm run lint` (frontend) | ✅ no errors |
| `npm run format:check` (frontend, Prettier) | ✅ all files formatted |
| `docker compose up -d --build` | ✅ postgres, backend, frontend all `Up`/`healthy` |
| `alembic upgrade head` (in the `backend` container) | ✅ applied `0001` |
| `psql -c "\dx"` | ✅ `vector 0.8.6` extension listed |
| `curl http://localhost:8000/health` | ✅ `{"status":"ok"}` |
| `curl http://localhost:3000` | ✅ HTTP 200, dashboard HTML confirmed (title + cards present) |

### Not done in this phase (intentionally)

Authentication, RAG, tickets, and any OpenAI integration. The `OPENAI_API_KEY` env var slot
exists in `.env.example`/`Settings` but is unused.

### Remaining/known issues going into Phase 2

- Browser-side verification of the dashboard's live health-check card (the `SystemStatusCard`
  client component polling `/health` after hydration) was not done with an actual browser in
  this session — only via `curl` against both services independently and confirming the CORS
  config allows `http://localhost:3000`. Worth a manual browser check before/at the start of
  Phase 2.
- `frontend/.npmrc` is a machine-specific workaround (see problem #2). If this repo is cloned to
  a machine/path without a `&` in it, or without Git Bash at that exact path, it's harmless but
  unnecessary; if Git Bash is installed elsewhere, update the path.
- C: drive on this dev machine runs extremely low on free space; keep an eye on it before large
  `docker build`/`npm install`/`pip install` operations in future phases.

---

## Phase 2 — Authentication & Role-Based Access Control (2026-09-13)

### Goal

Add real user accounts: registration, login, JWT access tokens, revocable refresh tokens,
two roles (`EMPLOYEE`, `ADMIN`), RBAC dependencies on the backend, and matching frontend
pages/state (login, register, dashboard, a minimal admin page, role-aware nav). No tickets,
RAG, or user-management UI — those stay out of scope per the brief.

### What was added

**Database**
- `users` table: UUID PK, unique+indexed `email`, `password_hash`, `full_name`, native Postgres
  enum `role` (`EMPLOYEE`/`ADMIN`, indexed), `is_active`, `created_at`/`updated_at`. Migration
  `0002_create_users.py`.
- `refresh_tokens` table: UUID PK, `user_id` FK (`ON DELETE CASCADE`), unique+indexed
  `token_hash` (SHA-256 of the raw token — the raw value is never stored), `expires_at`,
  nullable `revoked_at`, `created_at`. Migration `0003_create_refresh_tokens.py`.

**Backend** (`backend/app/`)
- `core/security.py` — Argon2 password hashing (`argon2-cffi`), JWT access-token
  encode/decode (`PyJWT`, 15 min expiry), opaque refresh-token generation/hashing.
- `utils/validation.py` — shared password-strength rule (≥8 chars, upper/lower/digit/special),
  used by both the registration schema and the admin seed script.
- `models/user.py`, `models/refresh_token.py` — SQLAlchemy models matching the migrations.
- `schemas/auth.py`, `schemas/user.py` — `RegisterRequest`/`LoginRequest` (with validators that
  normalize email and enforce password strength) and `UserPublic` (deliberately excludes
  `password_hash`).
- `repositories/user_repository.py`, `repositories/refresh_token_repository.py` — plain data
  access, no business logic.
- `services/auth_service.py` — registration, authentication, and the token lifecycle
  (issue/rotate/revoke), raising domain exceptions (`EmailAlreadyRegisteredError`,
  `InvalidCredentialsError`, `AccountDisabledError`, `InvalidRefreshTokenError`) that the API
  layer maps to HTTP status codes. Kept HTTP-agnostic on purpose so it's testable without a
  request/response cycle.
- `api/deps.py` — `require_authenticated_user()` (401 if the Bearer token is missing/invalid/
  expired, or the user is inactive) and `require_admin()` (403 if the role isn't `ADMIN`),
  exactly matching the dependency names in the brief.
- `api/auth.py` — `POST /api/auth/{register,login,refresh,logout}`. Access tokens go in the
  JSON body; refresh tokens go **only** in an httpOnly, `SameSite=Lax` cookie scoped to
  `/api/auth` (never in a JSON body or readable by JS) — see "Refresh token delivery" below.
  `/register` and `/login` are rate-limited (`slowapi`, 10/min per IP).
- `api/users.py` — `GET /api/users/me` (any authenticated user) and `GET /api/users`
  (admin-only; the RBAC demo/test surface, since Phase 2 has no other business endpoint to
  exercise `require_admin()` against).
- `core/limiter.py`, wired into `main.py` alongside the two new routers.
- `scripts/seed_admin.py` (+ `scripts/seed-admin.sh` wrapper) — creates an `ADMIN` user from
  `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` env vars; no-ops if the user exists; refuses to run
  when `ENVIRONMENT=production`; re-validates the password against the same strength rule.

**Frontend** (`frontend/`)
- `lib/apiClient.ts` — fetch wrapper: always sends `credentials: "include"` (for the refresh
  cookie), attaches `Authorization: Bearer` when given a token, throws a typed `ApiError` with
  the backend's `detail` message on non-2xx responses.
- `features/auth/` — `api.ts` (thin wrappers per endpoint), `AuthContext.tsx` (holds the access
  token **in memory only**, never `localStorage`; on mount calls `/api/auth/refresh` once to
  silently restore a session from the httpOnly cookie), `useRequireAuth.ts` (redirects to
  `/login` if signed out, or away from a role-gated page if the role doesn't match),
  `LoginForm.tsx`/`RegisterForm.tsx`, `ProfileCard.tsx` (a live `GET /api/users/me` call — the
  dashboard's demo of a protected API request), `validation.ts` (mirrors the backend's password
  policy for immediate feedback).
- `app/login/page.tsx`, `app/register/page.tsx` — redirect to `/dashboard` if already signed in.
- `app/dashboard/page.tsx` — the former root page, moved here and protected by
  `useRequireAuth()`; gained the `NavBar` and `ProfileCard`, lost the "Authentication" **coming
  soon** placeholder (Phase 2 shipped it).
- `app/admin/page.tsx` — minimal placeholder gated by `useRequireAuth({ role: "ADMIN" })`;
  exists specifically to demonstrate frontend RBAC (an `EMPLOYEE` who navigates here is bounced
  back to `/dashboard`) alongside the backend's independent 403 enforcement.
- `app/page.tsx` (root) — now a client-side redirect to `/dashboard` or `/login` based on auth
  state, instead of being the dashboard itself.
- `components/NavBar.tsx` — shows an "Admin" link only when `user.role === "ADMIN"`.

### Why these choices

- **Refresh token delivery: httpOnly cookie, not the JSON body.** Storing a long-lived refresh
  token anywhere JS can read it (a JS variable, `localStorage`) means any XSS on the page can
  steal a credential that outlives the session. An httpOnly cookie is invisible to JS entirely.
  Since the frontend (`:3000`) and backend (`:8000`) are different **ports** but the same
  **host** (`localhost`), and browser cookie scoping ignores port, this works in local dev
  without needing HTTPS or a proxy — `credentials: "include"` on the fetch is enough, backed by
  the existing CORS config's explicit origin + `allow_credentials=True` (already true from
  Phase 1, no change needed).
- **Refresh tokens are stateful (a DB table), not a second JWT.** A JWT-only refresh token
  can't be revoked before its own expiry — there's nothing to delete. Since the brief requires
  a real `/api/auth/logout`, the refresh token has to be a server-side, revocable record. Each
  refresh call also **rotates** it (old one revoked, new one issued), so a stolen-but-unused
  refresh token becomes detectably invalid the next time the real client uses it.
- **Access tokens are still stateless JWTs**, kept short-lived (15 min) — verified without a DB
  round-trip on every request, with the refresh token as the (DB-checked) renewal path. Fairly
  standard access/refresh split.
- **Public registration always creates `EMPLOYEE`, never `ADMIN`.** There is no request field
  or endpoint that lets a caller choose their own role — otherwise RBAC would be trivially
  bypassable. The only way to get an `ADMIN` account is the dev-only seed script or (in a real
  deployment) direct DB access / a future admin-only user-management endpoint.
- **`GET /api/users` (admin-only) was added even though it's not explicitly in the brief.**
  `require_admin()` needs *some* real endpoint to protect for the "employee access" / "admin
  access" tests to mean anything beyond a throwaway ping route. Listing users is a natural,
  minimally-scoped admin capability that belongs entirely to the auth/users domain already
  built this phase — not a step toward tickets/RAG.

### Problems encountered & how they were resolved

1. **Alembic tried to create the `user_role` enum type twice and failed on the second one.**
   The migration explicitly ran `CREATE TYPE user_role ...` (with `checkfirst=True`), then
   called `op.create_table(...)` with a column typed as that same `postgresql.ENUM(...)`
   object — but SQLAlchemy's table-creation DDL visitor *also* tries to create any enum type
   referenced by a column, regardless of the earlier explicit call, and that second attempt has
   no "if not exists" guard. Postgres correctly rejected it: `DuplicateObject: type "user_role"
   already exists`. Fixed by passing `create_type=False` on the enum object used *inside* the
   table definition, so only the one explicit, checkfirst'd `CREATE TYPE` call runs. (Alembic's
   default transactional-DDL wrapping meant the failed first attempt rolled back cleanly with
   no partial state left behind — confirmed via `\dT`/`\dt` before retrying.)
2. **Ruff's `B008` rule flagged every `Depends(...)` in a function default** (FastAPI's normal
   dependency-injection idiom) as "don't call functions in argument defaults." This is a
   well-known false positive for FastAPI codebases — rewriting away from `Depends(...)` isn't
   an option, it's how FastAPI's DI works. Fixed with the documented, correct suppression:
   `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls = ["fastapi.Depends", ...]` in
   `pyproject.toml`, rather than scattering `# noqa` comments.
3. **mypy flagged the slowapi rate-limit exception handler** (`app.add_exception_handler`)
   because slowapi's handler is typed for `RateLimitExceeded` specifically, narrower than
   Starlette's generic `Callable[[Request, Exception], ...]` signature it expects. This is a
   known slowapi/Starlette typing mismatch, not a real bug — resolved with one targeted
   `# type: ignore[arg-type]` and a comment explaining why, rather than a broad ignore.
4. **PyJWT warned the dev JWT secret was too short** (`InsecureKeyLengthWarning`, 29 bytes vs.
   the 32-byte HMAC-SHA256 recommendation). The original placeholder
   (`dev-insecure-secret-change-me`) was a real, if minor, weakening even as a dev-only default.
   Lengthened it to `dev-insecure-secret-change-me-before-deploying-anywhere` (also arguably a
   clearer prompt to actually change it) everywhere it's defined: `config.py`'s default and
   both `.env.example` files.
5. **Playwright's `getByText()` matched two elements** (the nav bar's "Name · ROLE" span and
   the profile card's "Name" paragraph both contain the user's full name as a substring),
   failing with a strict-mode violation. Fixed with `{ exact: true }`, which only matches an
   element whose *entire* text content equals the string — the nav bar span's full text is
   "Name · ROLE", not just "Name", so it no longer matches.
6. **Phase 1's `tests/dashboard.spec.ts` broke** — not a regression, but a direct, intentional
   consequence of this phase's own requirement to protect `/dashboard` and use `/` as an
   auth-redirect. Rather than patch around it, updated the test to assert the new (correct)
   behavior: `/` now redirects to `/login` when signed out. The original assertion (the
   platform heading is visible) still exists, just moved into `tests/auth.spec.ts`'s register
   flow, where the heading is actually reachable now (post-login, on `/dashboard`).
7. **Docker Desktop needed a manual restart before this phase's `docker compose up` could run**
   — unrelated to this phase's code; the backend process was still in the same disk-full-crash
   state described in Phase 1's problem log. Not re-documenting the fix here; see Phase 1.

### Verification performed

| Check | Result |
|---|---|
| `alembic upgrade head` (users + refresh_tokens migrations) | ✅ applied `0002`, `0003` |
| `psql -d itsupport -c "\d users" / "\d refresh_tokens"` | ✅ columns, indexes, FK all as designed |
| `pytest` (backend, host venv, against the real Postgres DB) | ✅ 17 passed |
| `pytest` (backend, inside the Docker container) | ✅ 17 passed |
| `ruff check .` / `black --check .` / `mypy app` (backend) | ✅ all clean |
| `npm run lint` / `npm run format:check` / `tsc --noEmit` (frontend) | ✅ all clean |
| `npx playwright test` (5 e2e tests: redirect, register→dashboard→logout, login, wrong password) | ✅ 5 passed |
| Manual `curl` walkthrough: register → duplicate (409) → login → `/me` (200) → no-token `/me`
  (401) → employee on `/api/users` (403) → wrong password (401) → refresh rotation → reuse of
  rotated-out token (401) → logout → refresh after logout (401) | ✅ every case matched the
  expected status code |
| `scripts/seed-admin.sh` — first run seeds, second run no-ops, `ENVIRONMENT=production` refuses,
  seeded admin can log in and `GET /api/users` (200) | ✅ all four behaviors confirmed |
| Manual browser screenshots: `/login`, `/register`, `/dashboard` (as `EMPLOYEE`, no Admin nav
  link), `/admin` visited as `EMPLOYEE` (redirects back to `/dashboard`) | ✅ all rendered and
  behaved as designed |

### Backend test list (`backend/tests/test_auth.py`, 16 tests, plus the Phase 1 health check)

Registration: success, duplicate email (409), weak password (422), malformed email (422).
Login: success, wrong password (401), unknown email (401). Tokens: valid token accepted,
expired token rejected (401), garbage token rejected (401), no token rejected (401). RBAC:
employee denied on admin endpoint (403), admin allowed (200). Refresh/logout: rotation
invalidates the old token, refresh without a cookie fails (401), logout revokes the session.
Each test runs inside a savepoint-based transaction (SQLAlchemy 2.0's
`join_transaction_mode="create_savepoint"`) that's rolled back afterward, so the suite is safe
to run repeatedly against the shared dev database without leaving test users behind.

### Not done in this phase (intentionally)

Password reset, email verification, MFA, and any admin user-management UI beyond the
read-only `GET /api/users` list. RAG and ticketing remain untouched.

### Known issues going into Phase 3

- The access token is held only in memory (React state), so a hard page refresh always does one
  round-trip through `/api/auth/refresh` before the user appears signed in — a brief flash of
  the "Loading..." state on every reload. This is a deliberate security/UX trade-off (see "Why
  these choices" above), not a bug, but worth knowing if Phase 3 adds anything sensitive to the
  first-paint dashboard.
- Rate limiting on `/api/auth/register` and `/api/auth/login` (`slowapi`, in-memory storage) is
  per-process — it resets on every backend restart and doesn't share state across multiple
  backend replicas. Fine for this single-instance dev/portfolio deployment; a real multi-replica
  deployment would need `slowapi`'s Redis storage backend instead.
- `GET /api/users` returns *all* users with no pagination — acceptable at today's scale, would
  need pagination before Phase 3 adds any real volume of users.

---

## Phase 3 — Knowledge Base & Document Ingestion (2026-09-14)

### Goal

Build the real document ingestion pipeline: admins upload PDF/TXT/Markdown files; the backend
extracts text, cleans it, chunks it, generates embeddings, and stores everything in pgvector,
with a real `UPLOADING → PROCESSING → INDEXING → READY/FAILED` status progression employees and
admins can both observe. Explicitly **not** in scope: the AI chat/RAG query interface itself —
this phase only builds the ingestion side.

### What was added

**Database**
- `knowledge_documents`: UUID PK, `title`, `filename` (sanitized display name — never used to
  build a filesystem path), `description`, indexed `category`, `uploaded_by` (FK to `users`,
  `ON DELETE SET NULL`), native Postgres enum `status` (indexed), `version`, `storage_path`,
  `mime_type`, `file_size_bytes`, `error_message` (server-side only), timestamps. The last four
  columns aren't in the brief's literal field list but are needed to satisfy other explicit
  requirements (reindex needs the stored file; "store useful server-side error information"
  needs somewhere to put it). Migration `0004_create_knowledge_base.py`.
- `document_chunks`: UUID PK, `document_id` FK (`ON DELETE CASCADE`), `chunk_index`, `content`,
  `page_number`, `metadata` (JSONB — mapped to the Python attribute `chunk_metadata` since
  `metadata` is a reserved name on SQLAlchemy declarative models), `embedding` (`vector(1536)`
  via `pgvector.sqlalchemy.Vector`), `created_at`. A unique constraint on
  `(document_id, chunk_index)` and an HNSW cosine-distance index on `embedding` (pgvector 0.8.6,
  bundled in the `pgvector/pgvector:pg16` image, supports HNSW natively).

**Backend** (`backend/app/`)
- `services/document_parser.py` — extension/size/magic-byte validation (PDF must start with
  `%PDF-`, not just have a `.pdf` extension), filename sanitization for display, `pypdf`-based
  PDF text extraction (per-page, capturing `page_number`), plain-text/Markdown extraction, and
  whitespace/control-character cleaning that preserves paragraph (blank-line) boundaries.
- `services/chunking_service.py` — paragraph-aware, token-bounded chunking:
  packs whole paragraphs up to `chunk_size_tokens` (default 1000), carries the trailing
  paragraphs of a finished chunk into the next one for `chunk_overlap_tokens` (default 150) of
  overlap, and only hard-splits a paragraph mid-way in the rare case a single paragraph alone
  exceeds the chunk budget. Uses `tiktoken`'s `cl100k_base` encoding purely as a sizing
  approximation (see "Why these choices").
- `services/embedding_service.py` — the only module that calls the embeddings API (Google
  Gemini, see the OpenAI→Gemini pivot below); batches requests (100 texts/call), raises
  `EmbeddingConfigurationError` (no key configured) or `EmbeddingGenerationError` (API/network
  failure), and accepts an injectable `client` so tests can substitute a fake without touching
  the network.
- `services/document_service.py` — orchestrates the pipeline end to end: `create_document`
  (validate, store the file under `storage/uploads/<document id>.<ext>`, insert the DB row with
  status `UPLOADING`) and `process_document` (extract → clean → chunk → embed → persist →
  `READY`, or catch any exception and mark `FAILED` with a truncated, safe error message).
  `process_document` accepts an optional `db` session — production/background-task callers omit
  it (get their own connection); tests pass the test's own session (see the isolation problem
  below). Also `start_reindex` (bumps `version`, resets to `UPLOADING`) and `delete_document`
  (DB row cascades to chunks; the stored file is removed separately).
- `repositories/document_repository.py`, `repositories/chunk_repository.py` — plain data access
  (list/get/create/update-status for documents; bulk-create/replace for chunks).
- `api/knowledge.py` — `GET /api/knowledge` and `GET /api/knowledge/{id}` (any authenticated
  user; employees only ever see `READY` documents, admins see every status — one endpoint,
  role-based filtering, rather than a separate admin-only listing route) and, under
  `/api/admin/knowledge` (`require_admin`): `POST /upload` (multipart; returns 202 immediately
  with status `UPLOADING`, schedules the real pipeline as a FastAPI `BackgroundTask`), `DELETE
  /{id}`, `POST /{id}/reindex`.
- `app/seed_data/knowledge_base/*.md` (8 files) + `scripts/seed_knowledge_base.py` — realistic
  demo IT documentation (VPN setup, password reset, Wi-Fi config, GitHub access policy,
  lost/stolen laptop procedure, software installation policy, remote work security policy, MFA
  setup), each opening with a **DEMO COMPANY DOCUMENTATION** banner making clear it's fictional.
  The script runs the *real* `document_service` pipeline synchronously (not a background task —
  there's no running app in a standalone script) against an existing admin user, and is
  idempotent (skips titles that already exist).

**Frontend** (`frontend/`)
- `lib/apiClient.ts` — updated to skip the `Content-Type: application/json` header when the
  request body is a `FormData` (file upload), letting the browser set its own multipart
  boundary.
- `features/knowledge/` — `api.ts` (thin per-endpoint wrappers), `useKnowledgeDocuments.ts`
  (fetches the full visible list and polls every 3s while any document is
  `UPLOADING`/`PROCESSING`/`INDEXING`), `StatusBadge.tsx`, `DocumentCard.tsx` (title, category,
  description, status, and — admin-only — Re-index/Delete buttons), `UploadForm.tsx`
  (drag-and-drop zone plus title/category/description fields, admin-only).
- `app/knowledge/page.tsx` — the document list; category/search filtering happens client-side
  over one unfiltered fetch (see "Why these choices").
- `app/knowledge/[id]/page.tsx` — full document detail, including the server-side
  `error_message` for admins on a `FAILED` document, and re-index/delete actions.
- `app/knowledge/upload/page.tsx` — admin-only (`useRequireAuth({ role: "ADMIN" })`).
- `components/NavBar.tsx` — added a "Knowledge Base" link (visible to every signed-in user);
  the "Admin" link stays admin-only as it was in Phase 2.
- `app/dashboard/page.tsx` — removed the now-implemented "Knowledge Base" **coming soon**
  placeholder card (same pattern as Phase 2 retiring the "Authentication" placeholder); bumped
  the phase indicator to 3/9; the "AI Assistant" placeholder's description no longer names a
  specific provider, since the chat/RAG provider isn't decided yet.

### Why these choices

- **Document processing runs in a FastAPI `BackgroundTask`, not synchronously in the request.**
  The brief's five-state status enum only means something if a client can actually observe a
  document mid-pipeline. A synchronous request would flash through every status in milliseconds
  and the frontend would only ever see the terminal state. `BackgroundTasks` gives real
  async progression without pulling in a task queue (Celery/Redis) this early — a
  proportionate choice for this phase's scope, revisitable later if ingestion volume grows.
- **Uploaded files are stored on disk keyed by the document's UUID**
  (`storage/uploads/<uuid>.<ext>`), not by the (sanitized) original filename. This sidesteps
  path-traversal and filename-collision concerns entirely at the storage layer — there's no
  user-controlled path component at all — while the sanitized original filename is still kept
  in the DB purely for display.
- **Employees and admins share one `GET /api/knowledge` endpoint**, filtered by role
  (`is_admin` → all statuses; otherwise `READY` only) rather than a separate admin-only listing
  route. The brief's frontend requirements ask for both "employee: document list" and "admin:
  processing status" — one endpoint with a role-based visibility rule satisfies both without
  duplicating the query logic, and a non-admin fetching a hidden document by ID gets a plain
  404 (not 403), the same "don't confirm what you can't see" pattern used for the admin-only
  user list in Phase 2.
- **Category/search filtering happens client-side** over a single unfiltered fetch, rather than
  passing `category`/`search` through to every request. Deriving the category dropdown's
  options from an *already-filtered* server response has an obvious bug — the dropdown shrinks
  to whatever's currently selected, making it impossible to switch categories without resetting
  first. At today's scale (dozens of documents, not thousands) client-side filtering avoids
  that bug and a second network round-trip; the backend's `category`/`search` query parameters
  still exist and are exercised directly by the backend test suite, so server-side filtering
  is available if/when the frontend needs it at larger scale.
- **`tiktoken`'s `cl100k_base` encoding sizes chunks even though embeddings come from Gemini,
  not OpenAI.** Gemini doesn't publish a tiktoken-compatible tokenizer. `cl100k_base` is used
  purely as a widely-available approximation for keeping chunks in the "approximately 800–1200
  tokens" range the brief asks for — it doesn't need to match the embedding model's own
  tokenizer exactly, just keep chunks in the right ballpark.

### The OpenAI → Gemini pivot

The brief specified OpenAI embeddings. The backend was built that way first — `openai` SDK,
`OPENAI_API_KEY`, `text-embedding-3-small` — and passed every mocked unit test. Live
verification then surfaced two real-world blockers in sequence:

1. The configured `OPENAI_API_KEY` had no billing credits (`429 insufficient_quota /
   credit_balance_exhausted` from the real API — the key itself was valid, confirmed by getting
   a quota error rather than an auth error).
2. Asked how to proceed, the user provided a Google Gemini API key instead and asked not to use
   OpenAI at all.

The switch touched exactly one service module (`embedding_service.py`, rewritten against
`google-genai`'s `Client.models.embed_content`) plus settings/env templates
(`OPENAI_API_KEY` → `GEMINI_API_KEY`, `embedding_model` default → `gemini-embedding-001`) and a
few comments/docs. **No migration or model change was needed** — Gemini's embedding models
support an `output_dimensionality` parameter, so `gemini-embedding-001` was configured to
output the same 1536 dimensions the `document_chunks.embedding` column already expected.
`document_service.py`, `chunking_service.py`, the API layer, and the DB schema are all
provider-agnostic and didn't change. The `openai` package was removed from `requirements.txt`
entirely (nothing else in the codebase used it) rather than left as dead weight.

Real verification against the live Gemini API (`test_generate_embeddings_against_real_gemini_api`,
and the full demo knowledge-base seed) both succeeded — see "Verification performed" below,
including a genuine semantic-similarity sanity check (MFA Setup Guide's nearest neighbor by
cosine distance was Password Reset Procedure — both are account-security documents).

### Problems encountered & how they were resolved

1. **`Annotated[KnowledgeDocumentUploadMeta, Form()]` (a Pydantic model bound to multipart form
   fields) failed with `{"loc": ["body", "meta"], "msg": "Field required"}`** even though
   `title`/`category`/`description` were sent as top-level form fields — FastAPI's handling of
   this pattern in the installed version didn't behave as the "flatten the model's fields into
   the form" documentation suggested when combined with a separate `File(...)` parameter in the
   same signature. Fixed by dropping the model-as-Form approach entirely in favor of
   individual, well-established `title: str = Form(...)` parameters — simpler and reliably
   correct across FastAPI versions, at the cost of one small inline blank-check instead of a
   Pydantic validator.
2. **Ruff's `B008` flagged `File(...)`/`Form(...)` in argument defaults**, the same false
   positive as Phase 2's `Depends(...)` issue. Extended the existing
   `extend-immutable-calls` allowlist in `pyproject.toml` (`fastapi.File`, `fastapi.Form`)
   rather than re-litigating the suppression per occurrence.
3. **A cross-connection test-isolation bug**: `document_service.process_document` opens its own
   `SessionLocal()` (correct for a real background task, which runs after the request's session
   has closed) — but the test suite's `db_session` fixture runs each test inside one outer,
   never-truly-committed transaction (Phase 2's `join_transaction_mode="create_savepoint"`
   pattern). A *second*, independent connection genuinely cannot see a *first* connection's
   uncommitted rows under Postgres's default isolation — so calling `process_document` from a
   test (via the scheduled background task) would silently find "no such document" and no-op.
   Fixed by giving `process_document` an optional `db: Session | None` parameter: production
   and the seed script omit it (unchanged behavior, own connection); tests pass the test's own
   session explicitly, running the pipeline inside the same transaction as everything else in
   that test. This also made tests fully synchronous and deterministic — no reliance on
   `TestClient`'s background-task timing, no polling needed.
4. **mypy flagged `list[str]` passed as `google.genai`'s `contents` parameter** as incompatible
   with its (enormous) declared union type — a false positive caused by `list`'s type
   invariance (`list[str]` isn't a `list[str | Image | ...]` even though every element trivially
   satisfies the union), the same category of issue as Phase 2's slowapi handler. Resolved with
   one targeted, commented `# type: ignore[arg-type]`, verified safe by the fact that the real
   API call it guards was exercised successfully against live Gemini.
5. **A new (to this codebase) ESLint rule, `react-hooks/set-state-in-effect`, failed the build**
   for `useKnowledgeDocuments.ts` and the document detail page — both called an async
   fetch-and-`setState` function directly from inside a `useEffect`. Phase 2's `AuthContext`
   already had working code that fetches on mount and doesn't trip this rule, by using a
   `.then()/.catch()` promise chain in the effect body instead of an `async` function invoked
   directly. Rewrote both new call sites to match that existing pattern rather than reaching
   for a rule-disable comment.
6. **Next.js's dev server (Turbopack) 404'd on every new route** (`/knowledge`,
   `/knowledge/upload`, `/knowledge/[id]`) even though the files existed on disk (confirmed
   inside the running container) and unrelated hot-reloads were working fine. This is a known
   dev-server quirk: content *edits* to existing route files hot-reload immediately, but
   *brand-new* route folders sometimes aren't picked up by the running dev server's route
   manifest until it restarts. Fixed with `docker compose restart frontend`; not a code bug.
7. **Ad-hoc Playwright screenshot scripts left zombie `chrome.exe` processes** (up to ~19,
   several hundred MB combined) after one script hit a selector error mid-run and never reached
   `browser.close()`. On this machine's chronically-low-disk C: drive (~200MB free — a
   pre-existing condition, see Phase 1), the accumulated zombies were enough to crash the *next*
   real `npx playwright test` run entirely (`Target crashed`, exit code 3221226505 /
   `STATUS_ACCESS_VIOLATION`) — a resource-exhaustion crash, not a regression in the app under
   test. Resolved by killing leftover `chrome.exe` processes before re-running; saved as a
   memory note for future sessions on this machine.

### Verification performed

| Check | Result |
|---|---|
| `alembic upgrade head` (knowledge_documents + document_chunks) | ✅ applied `0004` cleanly (no retry needed this time — applied the Phase 2 enum-migration lesson proactively) |
| `psql -d itsupport -c "\d knowledge_documents" / "\d document_chunks"` | ✅ columns, indexes (incl. HNSW), FK all as designed |
| `pytest` (backend, host venv and inside the Docker container) | ✅ 38 passed (20 knowledge-base + 17 auth + 1 health), including the real Gemini integration test once a key was configured |
| `ruff check .` / `black --check .` / `mypy app` (backend) | ✅ all clean |
| `npm run lint` / `npm run format:check` / `tsc --noEmit` (frontend) | ✅ all clean |
| `npx playwright test` (existing 5 auth/dashboard e2e tests) | ✅ 5 passed (after clearing the zombie-chrome resource issue above — confirmed not a regression) |
| Manual `curl` walkthrough: upload → immediate `UPLOADING` response → poll to `READY` with real chunk count → category filter → search → employee sees only `READY` (403 on upload) → reindex (version bumped, chunks regenerated) → delete (204, then 404, file removed from disk) | ✅ every case matched the expected status/behavior |
| **Real end-to-end pipeline**: `scripts/seed-knowledge.sh` against the live Gemini API | ✅ all 8 demo documents reached `READY`; verified directly in Postgres that every chunk has a genuine 1536-dimension embedding (`vector_dims(embedding) = 1536` for all rows) |
| **Real pgvector similarity search** (`embedding <=> ...` cosine distance, raw SQL, no app code) | ✅ semantically meaningful: "MFA Setup Guide"'s nearest neighbor was "Password Reset Procedure" (both account-security topics), confirming the stored embeddings are real and usable, not placeholder noise |
| Manual browser screenshots: `/knowledge` as ADMIN (all 8 docs, Re-index/Delete visible), `/knowledge/upload`, `/knowledge/{id}` detail, `/knowledge` as a freshly-registered EMPLOYEE (same 8 docs, no Upload button, no admin action buttons, no Admin nav link) | ✅ all rendered and behaved as designed |

### Backend test list (`backend/tests/test_knowledge.py`, 20 tests + 1 real-API integration test)

Upload: valid PDF (2-page, page numbers captured), valid TXT, valid Markdown, unsupported file
type (415), oversized file (413). Extraction: TXT, PDF (per-page). Chunking: size/paragraph
preservation, overlap between consecutive chunks, hard-split of one oversized paragraph.
Metadata + embeddings: `chunk_metadata.token_count` populated, every embedding is exactly
`settings.embedding_dimensions` long. Persistence: document/chunk row counts and FK linkage
match the API's reported `chunk_count`. Failure handling: a simulated embedding-API failure
correctly lands the document on `FAILED` with a non-empty `error_message`. Authorization:
upload/delete/reindex require `ADMIN` (403 for `EMPLOYEE`, 401 unauthenticated); employees can
view `READY` documents but never see a `FAILED`/in-flight one (404, not 403). Delete/reindex:
chunks and the stored file are actually removed; reindex regenerates chunks and bumps
`version`. Search/category filtering via the real API. A `pytest.mark.skipif`-gated integration
test calls the real Gemini embeddings API and is skipped automatically when `GEMINI_API_KEY`
isn't configured — exactly the "mock in unit tests, use the real API when configured" split the
brief asks for.

### Not done in this phase (intentionally)

The AI chat/RAG interface (querying the stored embeddings) — this phase only builds ingestion.
No admin user-management UI, no ticketing. See `PROJECT_INFO.md`'s "Explicitly out of scope for
Phase 3" for the full list (file types beyond PDF/TXT/MD, object storage, a categories
endpoint, document version history/rollback, bulk operations).

### Known issues going into Phase 4

- Demo documents seeded via `scripts/seed_knowledge_base.py` each produced exactly one chunk
  (they're realistic but short — a few hundred words each), so the chunking pipeline's
  size/overlap logic is verified thoroughly by the test suite's synthetic long-text cases, but
  the demo data itself isn't a great visual example of a *multi-chunk* document. A real
  multi-page PDF (verified manually via the README's own file, which produced 3 chunks) shows
  this better than the demo set does.
- Uploaded files live on the backend container's local filesystem
  (`backend/storage/uploads/`), tied to that one container/host. Fine for this single-instance
  dev/portfolio deployment; a real deployment would need object storage (S3-compatible) so
  uploads survive container replacement and work across multiple backend replicas.
- No pagination on `GET /api/knowledge` — same acceptable-for-now gap as Phase 2's user list,
  worth revisiting if the demo/real document count grows into the hundreds.
