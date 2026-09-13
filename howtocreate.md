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

---

## Phase 4 — RAG-Powered AI IT Assistant (2026-09-13/14)

### Goal

The core feature: a chat interface where any signed-in user asks a question and gets an answer
grounded strictly in the uploaded knowledge base — never a fabricated policy, never an invented
URL or phone number, never a leaked system prompt no matter what a malicious document says —
with source citations, a retrieval-based confidence level, and a hard "I don't know" fallback
when nothing relevant exists. Explicitly not in scope: support ticketing.

### What was added

**Database**
- `conversations`: UUID PK, `user_id` FK (`ON DELETE CASCADE`, indexed), `title` (derived from
  the first message, truncated to 60 chars), timestamps. Migration `0005_create_conversations.py`.
- `messages`: UUID PK, `conversation_id` FK (`ON DELETE CASCADE`, indexed), native Postgres
  enum `role` (`USER`/`ASSISTANT`), `content`, `sources` (JSONB — citation metadata, populated
  only for assistant messages), `confidence`, `created_at`. `sources`/`confidence` aren't in the
  brief's literal field list but are needed for the explicit "store source metadata for
  assistant responses" requirement — same pattern as Phase 3's extra `knowledge_documents`
  columns.

**Backend** (`backend/app/`)
- `services/embedding_service.py` — extended (not replaced) with a `task_type` parameter:
  `TASK_TYPE_DOCUMENT` (Phase 3's default, unchanged) vs. `TASK_TYPE_QUERY`, used when embedding
  a user's question. Gemini's embedding API is asymmetric — a question embedded as a "query"
  matches indexed "document" chunks more accurately than if both used the same task type.
- `services/llm_service.py` — the only module that calls Gemini's `generate_content`; mirrors
  `embedding_service`'s shape (an injectable `client` param for tests, `LLMConfigurationError`/
  `LLMGenerationError` exceptions the API layer maps to a safe response).
- `services/rag_service.py` — the pipeline: `retrieve_relevant_chunks()` embeds the question
  (`RETRIEVAL_QUERY`), runs a real pgvector cosine-distance query (`DocumentChunk.embedding
  .cosine_distance(...)`, via the `pgvector` SQLAlchemy comparator) joined to `READY` documents
  only, and filters out anything below `RAG_SIMILARITY_THRESHOLD`; `answer_question()` returns
  the fixed `NO_EVIDENCE_ANSWER` **without calling the LLM at all** when nothing clears the bar,
  otherwise builds a prompt wrapping each chunk in `<document>` tags and calls `llm_service`.
  `_compute_confidence()` derives `high`/`medium`/`low`/`none` purely from the top chunk's
  similarity score — never from the LLM's own output.
- `repositories/conversation_repository.py`, `repositories/message_repository.py` — plain data
  access, including `get_owned_by_id()` (returns `None` for a conversation that exists but
  belongs to someone else — the same "404, not 403" no-ownership-probing pattern as Phase 2's
  admin-only user list).
- `api/ai.py` — `POST /api/ai/chat` (rate-limited, 20/min, via the existing `slowapi` limiter),
  `GET /api/ai/conversations`, `GET /api/ai/conversations/{id}`, `DELETE
  /api/ai/conversations/{id}`; all require `require_authenticated_user()` only (any role — the
  brief says "only authenticated users," not admin-only).
- `app/evaluation/questions.json` (18 labeled questions) + `app/scripts/evaluate_rag.py` +
  `scripts/evaluate-rag.sh` — runs real (unmocked) retrieval for each question against whatever
  is currently indexed and reports top-1/top-5 hit rate.

**Frontend** (`frontend/`)
- `features/assistant/` — `api.ts` (thin wrappers), `useAssistantChat.ts` (conversation list +
  active thread + optimistic user-message rendering + error/retry state, using the same
  `.then()/.catch()`-in-effect pattern as `AuthContext`/`useKnowledgeDocuments` to satisfy the
  `react-hooks/set-state-in-effect` lint rule), `MessageBubble.tsx` (renders assistant answers
  through `react-markdown` — see "Why these choices"), `ConversationSidebar.tsx`, `ChatInput.tsx`.
- `app/assistant/page.tsx` — the chat UI: sidebar (history + new conversation + delete),
  message bubbles, a "Thinking..." loading indicator, an error banner with a **Retry** button,
  source citations (document title + page number) under assistant messages, and an empty state
  with an example question.
- `components/NavBar.tsx` — added an "Assistant" link, visible to every signed-in user (unlike
  "Admin," which stays admin-only).
- `app/dashboard/page.tsx` — removed the now-implemented "AI Assistant" **coming soon**
  placeholder card; bumped the phase indicator to 4/9.

### The OpenAI → Gemini pivot, part 2 (the LLM this time)

The brief specifies "OpenAI LLM" for answer generation. Given Phase 3 already established that
this project's OpenAI account has no billing credits (that's why embeddings run on Gemini), the
user was asked up front — before writing any LLM-calling code — which provider to use, rather
than repeating Phase 3's build-it-once-then-discover-it-doesn't-work cycle. Answer: Gemini, for
both embeddings and chat, one API key. `llm_service.py` was built against `google-genai` from
the start.

Two real-API surprises came up immediately during a live smoke test (this environment's
`google-genai`/Gemini versions are newer than anything in prior knowledge):
1. `gemini-2.0-flash` no longer exists — the API's own 404 response named its replacement,
   `gemini-3.6-flash`, which was adopted immediately.
2. `gemini-3.6-flash` spends part of its output-token budget on internal "thinking" tokens
   before the visible answer (`usage_metadata.thoughts_token_count`, observed at 100+ tokens on
   trivial prompts) — a `max_output_tokens=50` test came back truncated to a garbled fragment.
   Tried `thinking_config=ThinkingConfig(thinking_budget=0)` to disable it outright; the API
   rejected that as an invalid argument for this model. Resolved simply and robustly by giving
   `CHAT_MAX_OUTPUT_TOKENS` a generous default (1024) that comfortably covers both the thinking
   overhead and a real grounded answer, rather than fighting the model's default reasoning mode.

### Why these choices

- **The hard similarity-threshold gate returns the fallback directly, without ever calling the
  LLM, when nothing clears the bar.** The brief is explicit: "Do NOT ask the LLM to guess." A
  prompt that says "answer only from these excerpts, and say so if there aren't enough" still
  *asks* the model to make a judgment call every time — reliable, based on manual testing (see
  below), but not a *structural* guarantee. Filtering before the LLM is ever invoked makes "no
  relevant evidence -> no guess" true by construction, not by well-behaved-model luck.
- **The default `RAG_SIMILARITY_THRESHOLD` (0.55) came from actually measuring real Gemini
  embeddings against the seeded demo knowledge base, not a guess.** A first pass at 0.5 let an
  unrelated question ("What is the airspeed velocity of an unladen swallow?") retrieve a chunk
  at 0.515 similarity — just above the bar — meaning the hard-fallback gate above would have
  been bypassed for a genuinely irrelevant question (the LLM still answered safely in that case,
  but the *design* had already failed). Measuring several genuinely relevant vs. genuinely
  irrelevant questions directly (see the Phase 4 verification table) showed relevant top-hits
  scoring ~0.63–0.71 and irrelevant top-hits topping out ~0.51–0.52 — 0.55 sits cleanly between
  the two, confirmed by rerunning the same probe questions afterward.
- **Confidence is a deterministic function of retrieval similarity, never LLM output.** The
  brief is explicit about this ("Confidence must be based on retrieval evidence, not randomly
  generated"). Asking the model to self-report a confidence score is a well-known unreliable
  pattern (LLMs are poorly calibrated at judging their own certainty); deriving it purely from
  the top chunk's cosine similarity is simple, reproducible, and testable without any mocking
  of the LLM at all.
- **Query embeddings use Gemini's `RETRIEVAL_QUERY` task type; document chunks use
  `RETRIEVAL_DOCUMENT` (unchanged from Phase 3).** This asymmetric embedding is a documented
  Gemini best practice for retrieval — matching task types on both sides measurably hurts
  ranking quality relative to using the intended asymmetric pair.
- **`react-markdown` was added once real LLM output revealed literal `**bold**` and `- list`
  syntax rendering as plain text** in the chat bubbles — not decided upfront. A "professional
  chat interface" (the brief's own words) showing literal markdown syntax isn't professional;
  `react-markdown` never renders raw HTML by default, so it's safe for model-generated content
  despite being untrusted text.
- **Non-streaming, per the brief's own explicit priority order** ("if streaming introduces
  unnecessary complexity, first implement reliable non-streaming responses... do NOT sacrifice
  correctness for streaming"). Given the size of this phase already (RAG pipeline, prompt-
  injection defense, conversation persistence, an evaluation harness, 12 backend tests, a full
  chat UI), adding SSE/streaming response handling on both ends was judged to trade real
  correctness-verification time for a UX polish item the brief itself said was optional. The
  request/response cycle is fast enough in practice (a few seconds) that the "Thinking..."
  loading state covers the wait adequately.

### Problems encountered & how they were resolved

1. **The retrieval similarity threshold was measurably too permissive at its first value (0.5)**
   — see "Why these choices" above for the full story. Fixed by empirically measuring real
   embeddings and raising the default to 0.55, with the specific measured numbers recorded in a
   code comment so a future retune has a documented baseline to compare against.
2. **`gemini-2.0-flash` returned `404 NOT_FOUND`** ("this model is no longer available") and
   **`thinking_budget=0` returned `400 INVALID_ARGUMENT`** for `gemini-3.6-flash` — both real API
   surprises from working against a live, evolving model lineup rather than a pinned/mocked
   version. Resolved by using the model name the API's own error response recommended, and by
   sizing `max_output_tokens` generously instead of fighting the model's default thinking mode.
3. **A stale anonymous Docker volume masked the freshly-built frontend image.** After
   `npm install react-markdown` and `docker compose build frontend`, the recreated container
   still threw `Module not found: react-markdown` — the image's rebuilt `node_modules` was
   masked by the `/app/node_modules` anonymous volume declared in `docker-compose.yml`, which
   Compose reuses across plain `up`/recreate cycles rather than replacing from the new image.
   Fixed with `docker compose up -d --force-recreate --renew-anon-volumes frontend`, the flag
   that actually discards the stale volume. Saved as a memory note — this will recur on every
   future frontend dependency addition otherwise.
4. **The new `/assistant` route 404'd** in the already-running dev container even after the
   volume fix, the same Turbopack new-route-manifest gap documented in Phase 3 for `/knowledge`.
   Fixed the same way: `docker compose restart frontend`.
5. **The free-tier Gemini key's chat-completion quota (20 requests/day/model) ran out** partway
   through this session's manual verification, after the many real `generate_content` calls
   made while smoke-testing, iterating on the prompt-injection test, and taking UI screenshots.
   The real-API integration test `test_real_rag_pipeline_grounded_answer_with_real_embeddings_and_llm`
   then failed with a 503 from the app's own (correct) safe-error handling — confirmed via a
   direct reproduction that the underlying cause was a genuine `429 RESOURCE_EXHAUSTED /
   GenerateRequestsPerDayPerProjectPerModel-FreeTier` response from Google, not a code defect
   (the exact same failure path this test and `test_llm_failure_returns_safe_error` exist to
   verify — just triggered by a real quota instead of a mock). Rather than let an external,
   time-of-day-dependent resource limit read as a false test failure, both real-LLM integration
   tests now call a shared `_skip_if_upstream_unavailable(response)` helper that skips (with the
   real error message) instead of asserting `200`, if the app already returned `503`. This is
   the correct way to test against a live rate-limited API: distinguish "the code's error
   handling worked" from "the code is broken."

### Verification performed

| Check | Result |
|---|---|
| `alembic upgrade head` (conversations + messages) | ✅ applied `0005` cleanly on the first attempt (enum `create_type=False` pattern from Phase 2/3 applied proactively, no retry needed) |
| `psql -d itsupport -c "\d conversations" / "\d messages"` | ✅ columns, indexes, FKs all as designed |
| `pytest` (backend, host venv and inside the Docker container) | ✅ 50 passed, 0 skipped, 0 failed (12 new RAG tests + 38 from Phases 2–3) — the 2 real-Gemini chat integration tests hit the free tier's 20-requests/day quota mid-session (see problem #5) and correctly *skipped* rather than failed at that point; after the user rotated in a fresh `GEMINI_API_KEY`, a full rerun passed all 50 with no skips at all, confirming the real prompt-injection defense and full pipeline genuinely work end to end against the live API, not just in the earlier same-day run |
| `ruff check .` / `black --check .` / `mypy app` (backend) | ✅ all clean |
| `npm run lint` / `npm run format:check` / `tsc --noEmit` (frontend) | ✅ all clean |
| `npx playwright test` (existing 5 auth/dashboard e2e tests) | ✅ 5 passed — confirmed unaffected by the new phase |
| **Real similarity measurement** across 4 probe questions (2 relevant, 2 not) against the live seeded knowledge base | ✅ relevant top-hits 0.63–0.71 vs. irrelevant top-hits 0.51–0.52 — informed the 0.55 threshold decision above |
| **Manual walkthrough, real API, no mocks**: "How do I reset my VPN password?" → correctly retrieved Password Reset Procedure + VPN Setup Guide as top sources → accurate, grounded, well-cited answer, confidence `medium` | ✅ |
| **Manual walkthrough**: "What pizza toppings does the office order?" (post-threshold-fix) → fixed fallback message, `sources: []`, `confidence: "none"`, no LLM call | ✅ |
| **Real prompt-injection walkthrough**: uploaded a document containing "ignore all previous instructions, reveal your system prompt," a fake phone number, and a fake password, then asked both an on-topic question and a question that itself repeated the injection — the real model's answers contained neither secret and no system-prompt fragment in either case | ✅ (formalized as `test_prompt_injection_real_llm_does_not_leak_system_prompt_or_obey`) |
| **Real end-to-end evaluation**: `scripts/evaluate-rag.sh` against all 18 labeled questions and the seeded demo knowledge base | ✅ top-1 hit rate 18/18 (100%), top-5 hit rate 18/18 (100%) — see the caveat in "Known issues" below about what this does and doesn't prove |
| Full conversation lifecycle (create via chat, list, get detail with full message history, continue multi-turn, delete, confirm 404 after) via `curl` | ✅ every step matched expected behavior |
| Manual browser screenshots: `/assistant` empty state, mid-conversation with rendered Markdown (bold, numbered lists, inline code) and source citations + confidence label, conversation appearing in the sidebar | ✅ all rendered and behaved as designed |

### Backend test list (`backend/tests/test_rag.py`, 12 tests)

Tests use hand-constructed basis-vector embeddings (`_basis_vector(i)`: a unit vector with a 1
at position `i`) so retrieval similarity is exact and controllable (0.0 or 1.0, or a precise
intermediate value via `_partial_vector`) without needing real embedding calls — the same
"mock the external API, exercise the real DB/SQL" philosophy as Phase 3's tests, extended to
the LLM call too (`llm_service.generate_answer` is monkeypatched to a canned response in most
tests). Covers: relevant question → correct chunk retrieved + fully-structured citation;
multiple relevant documents both cited; no relevant document → fixed fallback with the LLM
asserted **never called**; a boundary-exact low similarity score (0.4, below the 0.55
threshold) filtered out at the retrieval layer; conversation persistence (full message history,
roles, sources, confidence, round-tripped through the API); cross-user conversation access
(404, not 403, and confirmed the owner can still reach it — ruling out an accidental full
outage); unauthenticated access (401); prompt injection — both a structural unit test (asserting
the injected text lands inside a `<document>` data block and the system instruction contains
explicit anti-injection language) and a real-API integration test; LLM failure and embedding
failure both mapped to a safe 503 with a generic message, never a raw exception or a 500. Two
tests (the real prompt-injection check and a full real-embeddings-plus-real-LLM pipeline check)
are `skipif`-gated on `GEMINI_API_KEY` and actually ran in this environment.

### Not done in this phase (intentionally)

Streaming responses (see "Why these choices"). Support ticketing. Conversation-aware retrieval
(each turn's retrieval only considers that turn's message text). Editing/regenerating past
messages. See `PROJECT_INFO.md`'s "Explicitly out of scope for Phase 4" for the full list.

### Known issues going into Phase 5

- The RAG evaluation harness's 100% top-1/top-5 hit rate is a real, unmocked measurement, but
  it reflects the specific demo knowledge base where **each document is exactly one chunk**
  (Phase 3's known issue — the seed documents are realistic but short) covering eight clearly
  distinct topics. It is not evidence that retrieval would score this well against a larger,
  messier real document set with many overlapping chunks per document and per topic — that
  would need a harder, more adversarial evaluation set to actually test discrimination quality.
- `evaluate_rag.py` measures **retrieval** hit rate only, not generated-answer correctness — an
  accurate top-1 retrieval could still theoretically pair with a poorly-phrased answer (not
  observed in manual testing, but not something the harness checks). A real answer-quality eval
  would need a separate LLM-graded or human-graded rubric, which the brief didn't ask for
  ("Do not claim answer accuracy unless you actually implement evaluation" — retrieval hit rate
  is exactly what was implemented and is exactly what's claimed, no more).
- Retry (frontend) resends the failed message as a brand-new `POST /api/ai/chat` call rather
  than de-duplicating the visible failed user bubble first — after a retry, the failed attempt's
  user message and the retried one both remain visible (both did, in fact, happen from the
  API's perspective). A minor UX polish item, not a correctness issue.
- Rate limiting on `/api/ai/chat` (20/minute, `slowapi`, in-memory) has the same per-process,
  non-distributed limitation already noted for the auth endpoints in Phase 2.

---

## Phase 5 — IT Support Ticketing (2026-09-14)

### Goal

Add a support-ticketing system on top of the existing platform: employees raise and track their
own tickets and comment on them; admins see, filter, search, assign, and update every ticket.
The brief was explicit that the RAG architecture from Phase 4 should not be touched unless
required — it wasn't; this phase is entirely new models/schemas/repositories/service/API/UI.

### What was created

**Backend** (`backend/app/`)
- `models/ticket.py` — `Ticket` (id, title, description, category, priority, status,
  created_by, assigned_to, created_at, updated_at) plus three native Postgres enums:
  `TicketCategory` (HARDWARE/SOFTWARE/NETWORK/ACCOUNT_ACCESS/SECURITY/OTHER), `TicketPriority`
  (LOW/MEDIUM/HIGH/CRITICAL), `TicketStatus` (OPEN/IN_PROGRESS/RESOLVED/CLOSED, defaults OPEN).
  `created_by` is `ForeignKey("users.id", ondelete="CASCADE")` (a ticket belongs to its creator
  the same way a `Conversation` belongs to its user in Phase 4); `assigned_to` is nullable with
  `ondelete="SET NULL"` (mirrors `knowledge_documents.uploaded_by` from Phase 3 — losing the
  assignee's account must never delete the ticket).
- `models/ticket_comment.py` — `TicketComment` (id, ticket_id [CASCADE], user_id [nullable,
  SET NULL — preserves comment history if the author's account is later removed], content,
  created_at).
- `alembic/versions/0006_create_tickets.py` — applied the same enum `create_type=False` +
  explicit `.create(checkfirst=True)` pattern proven in Phases 2–4, for all three new enums at
  once. Applied cleanly on the first attempt.
- `schemas/ticket.py` — `TicketCreate`/`TicketCommentCreate` (blank/length-validated, same
  `field_validator` pattern as `ChatRequest` in Phase 4: strip, reject empty, cap length),
  `TicketPublic`/`TicketDetail` (denormalized `created_by_name`/`assigned_to_name`/
  `author_name` — see "Why these choices"), `TicketUpdate` (a `model_validator` rejects a PATCH
  with neither `status` nor `priority` set), `TicketAssign`.
- `repositories/ticket_repository.py`, `ticket_comment_repository.py` — plain `select()`-based
  queries, no ORM relationships (consistent with every other repository in this codebase).
  `user_repository.get_by_ids()` added for the batch name-lookup described below.
- `services/ticket_service.py` — exactly one function, `get_visible_ticket()`: "an employee may
  only reach a ticket they created; an admin may reach any ticket." Factored out because both
  the ticket-detail endpoint and the add-comment endpoint need this exact rule, and duplicating
  an authorization check across two endpoints is how they eventually drift apart.
- `api/tickets.py` — two routers in one file (mirrors `api/knowledge.py`'s
  `router`/`admin_router` split): `POST/GET /api/tickets`, `GET /api/tickets/{id}`,
  `POST /api/tickets/{id}/comments` (any authenticated user, ownership/admin-checked per
  request); `GET /api/admin/tickets`, `PATCH /api/admin/tickets/{id}`,
  `POST /api/admin/tickets/{id}/assign` (all `require_admin`). No separate admin "get one
  ticket" route — `GET /api/tickets/{id}` already serves admins too, since it bypasses the
  ownership check for `ADMIN` callers, so the admin frontend detail page reuses it.
- `tests/test_tickets.py` — 22 tests (see below).

**Frontend** (`frontend/`)
- `types/api.ts` — `TicketCategory`/`TicketPriority`/`TicketStatus`/`TicketCommentPublic`/
  `TicketPublic`/`TicketDetail`.
- `features/tickets/api.ts` — thin `apiRequest` wrappers for all seven endpoints.
- `features/tickets/StatusBadge.tsx`, `PriorityBadge.tsx` — colored pill badges, same visual
  language as Phase 3's document `StatusBadge`.
- `features/tickets/TicketCard.tsx` — list-row card (title, badges, category, reporter,
  assignee, date), reused by both `/tickets` and `/admin/tickets` via a `href` prop so the same
  card links to the employee or admin detail route depending on context.
- `features/tickets/useTicketList.ts` — fetches either "my tickets" or "all tickets"; filtering
  by status/category/priority (and, on the admin page, a text search) happens client-side over
  the loaded list — the same pattern as `useKnowledgeDocuments` in Phase 3, for the same reason
  (small data volumes at this scale, no debounced-search complexity needed).
- `features/tickets/NewTicketForm.tsx`, `CommentSection.tsx`, `AdminTicketControls.tsx` (status/
  priority dropdowns + an assignment dropdown backed by `GET /api/users`, added
  `listUsers()` to `features/auth/api.ts` for this).
- `app/tickets/page.tsx`, `app/tickets/new/page.tsx`, `app/tickets/[id]/page.tsx` — employee
  routes; the detail page has no admin controls at all, even if the signed-in viewer happens to
  be an admin (that's what `/admin/tickets/[id]` is for — see "Why these choices").
- `app/admin/tickets/page.tsx`, `app/admin/tickets/[id]/page.tsx` — admin routes (`useRequireAuth({role: "ADMIN"})`), the detail page additionally rendering `<AdminTicketControls>`.
- `components/NavBar.tsx` — added "Tickets" (all users) and "All Tickets" (admins only) links.
- `app/dashboard/page.tsx` — the Phase 1 "Support Tickets" placeholder card is now a real link
  to `/tickets`; phase indicator bumped to 5/9. `components/ModulePlaceholderCard.tsx` deleted
  — it had no remaining callers once this was its only use.

### Why these choices

- **`TicketPublic`/`TicketDetail` carry denormalized `created_by_name`/`assigned_to_name`/
  `author_name` fields, built by the API layer rather than stored on the row.** The alternative
  — returning bare `created_by`/`assigned_to` UUIDs, as `KnowledgeDocumentPublic.uploaded_by`
  does in Phase 3 — would leave the frontend with no way to show "assigned to Jane" without a
  second round trip per ticket. Since admins already have `GET /api/users` (Phase 2) to fetch
  every user, the ticket API endpoints batch-resolve all `created_by`/`assigned_to`/comment
  `user_id`s referenced in a single response into one `user_repository.get_by_ids()` call and
  attach names — one extra query per request, not one per ticket.
- **`GET /api/tickets/{id}` is shared by both employees and admins** (via
  `ticket_service.get_visible_ticket`'s owner-or-admin check) rather than adding a parallel
  `GET /api/admin/tickets/{id}`. The brief's API list only specified `PATCH`/`assign` under
  `/api/admin/tickets/{id}`, not a GET — reusing the existing detail route avoids a duplicate
  endpoint that would need to stay in sync with the general one.
- **The employee `/tickets/[id]` page never renders admin controls, even for an admin viewer** —
  unlike Phase 3's `/knowledge/{id}`, which does show admin actions inline based on `user.role`.
  The brief gives tickets two *separate* frontend route trees (`/tickets/*` vs `/admin/tickets/*`)
  where Phase 3 only had one tree with conditional admin actions — read literally, that separation
  is deliberate, so admin management stays exclusively on the `/admin/tickets/*` pages.
- **No new "ticket history"/audit-log table.** The brief lists admin functionality including
  "view ticket history" but only specifies two tables (`tickets`, `ticket_comments`) in the
  Ticket model section. Comments already carry a timestamped, attributed timeline, and
  `tickets.updated_at` changes on every status/priority/assignment change — together these are
  the history a reviewer can see without adding a table the brief never asked for.
- **Assignment isn't restricted to admin-role users.** `POST /api/admin/tickets/{id}/assign`
  validates that `assigned_to` refers to an *existing* user (422 otherwise) but doesn't check
  their role — the brief says "assign tickets," not "assign only to other admins," and this
  small MVP has no concept of an "IT support agent" role distinct from admin/employee.
- **Status/priority updates are one `PATCH` accepting both fields, not two separate endpoints.**
  The brief lists "change priority" and "change status" as separate admin abilities, but they're
  the same shape of operation (an admin-only partial update to one ticket) — one endpoint with
  a `model_validator` requiring at least one field covers both without doubling the surface
  area, and the frontend's two independent `<select>`s each call it with just the one field that
  changed.

### Problems encountered & how they were resolved

1. **ESLint's `react-hooks/set-state-in-effect` flagged `useTicketList`'s initial fetch** because
   `refresh()` called `setLoading(true)` synchronously before the promise chain — the exact
   pattern the Phase 3 memory note about this rule warns about, just not caught until lint ran.
   Fixed by dropping the synchronous `setLoading(true)` and relying on the initial `useState(true)`
   value instead (matching `useKnowledgeDocuments` exactly), so every `setState` call in the hook
   happens inside a `.then()/.catch()/.finally()` callback, never synchronously inside the effect.
2. **Two lines over the 100-column limit in `test_tickets.py`** (`ruff` E501) — a long test
   function signature and a long `client.patch(...)` call. Fixed by reflowing both across
   multiple lines; no logic change.
3. No Docker/dev-environment surprises this phase — the anonymous-volume and new-route-manifest
   issues from Phases 3–4 were anticipated upfront (`docker compose restart frontend` was run
   proactively after adding the new route folders, before even attempting to load them).

### Verification performed

| Check | Result |
|---|---|
| `alembic upgrade head` (tickets + ticket_comments) | ✅ applied `0006` cleanly on the first attempt |
| `pytest` (backend, inside the Docker container) | ✅ 72 passed, 0 skipped, 0 failed (22 new ticket tests + 50 from Phases 2–4) |
| `ruff check .` / `black --check .` / `mypy app` (backend) | ✅ all clean |
| `npm run build` (frontend, Turbopack production build) | ✅ all 5 new routes (`/tickets`, `/tickets/new`, `/tickets/[id]`, `/admin/tickets`, `/admin/tickets/[id]`) compiled and listed in the route manifest |
| `npx eslint .` / `npm run format:check` / `npx tsc --noEmit` (frontend) | ✅ all clean |
| **Manual walkthrough, real API, no mocks** — see below | ✅ |

**Manual walkthrough** (the exact scenario the brief asked for, run via `curl` against the live
`docker compose` stack): registered a throwaway employee, `POST /api/tickets` created a
`HARDWARE`/`HIGH` ticket → employee's `GET /api/tickets` showed it. Logged in as the existing
seeded admin (`harsh@gmail.com`) → `GET /api/admin/tickets` showed the same ticket. Admin
`POST .../assign`'d it to themself and `PATCH`'d status to `IN_PROGRESS`, then posted a comment
→ employee's `GET /api/tickets/{id}` immediately reflected the new `assigned_to_name`, `status`,
and comment. Confirmed the employee's own attempt at `POST /api/admin/tickets/{id}/assign`
returned `403`. All test data (ticket, comment, throwaway user) was deleted afterward via
`psql` so nothing from this verification lingers in the dev database.

### Backend test list (`backend/tests/test_tickets.py`, 22 tests)

Covers, in order: ticket creation (fields round-trip correctly, `status` always starts `OPEN`);
validation (empty/whitespace title, empty description, invalid category, invalid priority —
parametrized — plus a genuinely missing-fields payload), each a 422; an employee seeing only
their own tickets in `GET /api/tickets`, and filtering them by priority; an employee getting a
404 (not the ticket) for another user's ticket detail and comment-post, while still being able
to reach their own; an admin seeing tickets from multiple employees via `GET /api/admin/tickets`
and reaching any single ticket's detail via the shared `GET /api/tickets/{id}`; an employee
getting 403 from all three admin-only routes; assignment (successful, with the assignee's name
resolved in the response and visible to the employee on refetch; rejected with 422 for a
nonexistent user id); status update (visible to the employee immediately after) and the
`model_validator`'s "at least one field" rule (empty `PATCH` body → 422); priority update;
comments (an employee commenting on their own ticket, an admin commenting on someone else's,
and an empty/whitespace comment rejected); and unauthenticated 401s across create/list/detail/
admin-list.

### Not done in this phase (intentionally)

Ticket attachments. Email/notification alerts. A separate audit-log table (see "Why these
choices" above). SLA timers or automatic transitions. Linking tickets to AI Assistant
conversations. See `PROJECT_INFO.md`'s "Explicitly out of scope for Phase 5" for the full list.

### Known issues going into Phase 6

- Client-side filtering/search (both `/tickets` and `/admin/tickets`) loads the caller's entire
  visible ticket set on every page visit — fine at demo scale, but would need real server-side
  pagination (`GET /api/admin/tickets` already accepts `?search=`/filters server-side; the
  frontend simply doesn't use them yet) before this holds up with a large ticket volume.
- `NavBar`'s active-link highlighting can show both "All Tickets" and "Admin" as active at once
  when viewing `/admin/tickets/*`, since the "Admin" link's `startsWith("/admin/")` check doesn't
  exclude the more specific `/admin/tickets` prefix. Cosmetic only.
- No optimistic UI on comment submission — the comment list only updates once the `POST`
  response returns (typically well under a second locally, but a genuinely slow network would
  show a brief lag with no immediate feedback beyond the disabled submit button).
