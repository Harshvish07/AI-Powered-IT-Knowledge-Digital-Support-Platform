# AI-Powered IT Knowledge & Digital Support Platform

A portfolio-quality platform combining an IT knowledge base, digital support tooling, and
AI-assisted (RAG) answers. This repository is being built in **9 phases**; this document is
kept up to date as each phase lands.

> **Current status: Phase 3 — Knowledge Base & Document Ingestion.**
> On top of Phase 2's auth/RBAC: admins can upload PDF/TXT/Markdown documents, which are
> extracted, chunked, embedded (Google Gemini), and stored in pgvector; employees can browse,
> search, and filter READY documents. The AI chat/RAG assistant and support ticketing are not
> implemented yet.

See [`PROJECT_INFO.md`](./PROJECT_INFO.md) for the phase roadmap and project-level context,
and [`howtocreate.md`](./howtocreate.md) for a running build log of what was done and why in
each phase.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL + pgvector |
| Document parsing | `pypdf` (PDF), plain-text/Markdown |
| Embeddings | Google Gemini API (`gemini-embedding-001`) |
| AI chat/RAG | Not implemented yet (later phase; provider not yet decided) |
| Infra | Docker, Docker Compose |
| Testing | Pytest (backend), Playwright (e2e) |

## Repository structure

```
project-root/
  frontend/            # Next.js app
    app/               # App Router pages: /, /login, /register, /dashboard, /admin,
                       #   /knowledge, /knowledge/[id], /knowledge/upload
    components/         # Shared UI components (incl. role-aware NavBar)
    features/           # Feature-scoped modules (features/auth/, features/knowledge/)
    hooks/               # React hooks
    lib/                 # Client utilities/config (incl. the API fetch wrapper)
    types/               # Shared TS types
    tests/               # Playwright e2e tests
  backend/             # FastAPI app
    app/
      api/               # Route definitions + auth/RBAC dependencies (deps.py)
      core/              # Config, DB session, security (hashing/JWT), rate limiter
      models/            # SQLAlchemy models
      schemas/           # Pydantic schemas
      services/          # Business logic (auth lifecycle; document ingestion pipeline)
      repositories/      # Data access
      scripts/           # One-off scripts (dev admin seed, demo knowledge-base seed)
      seed_data/         # Static demo content for the knowledge-base seed script
      storage/           # Uploaded files at runtime (gitignored, created on demand)
      utils/             # Helpers (e.g. password policy)
      workers/           # Background jobs (future — ingestion currently uses
                         #   FastAPI BackgroundTasks, not a separate worker)
      main.py
    alembic/             # DB migrations
    tests/               # Pytest tests
  docs/                # Architecture & design docs
  scripts/             # Dev helper scripts
  docker-compose.yml
  .env.example
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Node.js 20+ (only needed if running the frontend outside Docker)
- Python 3.12+ (only needed if running the backend outside Docker)

## Quick start (Docker — recommended)

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Start everything:
   ```bash
   docker compose up --build
   ```
3. Visit:
   - Frontend: http://localhost:3000
   - Backend health check: http://localhost:8000/health
4. Apply database migrations (enables the `pgvector` extension):
   ```bash
   docker compose exec backend alembic upgrade head
   ```

## Running services individually (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

## Testing & quality

### Backend

Backend tests exercise the real database (users/auth need Postgres — there's no SQLite
fallback), so Postgres must be running and migrated first:

```bash
docker compose up -d postgres
docker compose exec backend alembic upgrade head   # or: cd backend && alembic upgrade head
```

Then, from `backend/` (with `DATABASE_URL` pointing at that database — the default in
`.env.example` works if Postgres is exposed on `localhost:5432`):

```bash
cd backend
pytest                # run tests — each test runs in a rolled-back transaction
ruff check .          # lint
black --check .       # formatting check
mypy app              # type check
```

Knowledge-base tests mock the Gemini embedding call by default (no network access needed), so
the full suite passes without `GEMINI_API_KEY` set. One test
(`test_generate_embeddings_against_real_gemini_api`) calls the real API and is automatically
skipped unless `GEMINI_API_KEY` is configured.

### Frontend

```bash
cd frontend
npm run lint          # ESLint
npm run format:check  # Prettier check
npm run test:e2e      # Playwright e2e tests (requires `npx playwright install` once)
```

The e2e suite includes real login/register/logout flows, so the backend and database must
also be running (`docker compose up -d postgres backend`) before `npm run test:e2e`.

## Environment variables

See [`.env.example`](./.env.example) (root, used by Docker Compose) and
[`backend/.env.example`](./backend/.env.example) (used when running the backend standalone).
Never commit a real `.env` file — only `.env.example` templates are tracked in git.

## Database & pgvector

The `postgres` service uses the `pgvector/pgvector:pg16` image, which ships PostgreSQL 16 with
the `vector` extension available. The extension is enabled by the first Alembic migration:

```bash
docker compose exec backend alembic upgrade head
```

Verify it's enabled:

```bash
docker compose exec postgres psql -U postgres -d itsupport -c "\dx"
```

`document_chunks.embedding` is a `vector(1536)` column (matching Gemini's `gemini-embedding-001`
output dimension) with an HNSW cosine-distance index, ready for similarity search once the
AI/RAG assistant phase adds a query path:

```bash
docker compose exec postgres psql -U postgres -d itsupport -c "\d document_chunks"
```

You should see `vector` listed among the installed extensions.

## Authentication & roles

Two roles exist: `EMPLOYEE` (default for anyone who registers) and `ADMIN`. There is no
self-service way to become an admin — see "Seeding an admin user" below.

| Method | Path | Auth required | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | — | Creates an `EMPLOYEE` user; logs them in (returns tokens) |
| POST | `/api/auth/login` | — | Returns an access token; sets an httpOnly refresh cookie |
| POST | `/api/auth/refresh` | Refresh cookie | Rotates the refresh token, returns a new access token |
| POST | `/api/auth/logout` | Refresh cookie | Revokes the refresh token, clears the cookie |
| GET | `/api/users/me` | Bearer access token | The caller's own profile |
| GET | `/api/users` | Bearer access token, `ADMIN` role | Lists all users (403 for non-admins) |

The access token is a short-lived JWT (15 min by default) sent as `Authorization: Bearer
<token>` and kept in memory on the frontend (never `localStorage`). The refresh token is an
opaque, server-side-revocable token delivered only via an httpOnly cookie scoped to
`/api/auth` — JavaScript never sees it. On refresh/logout the token is rotated/revoked in the
`refresh_tokens` table, so a stolen refresh token stops working the next time it's used.

### Testing login manually

With the stack running (`docker compose up -d`, migrations applied):

```bash
# Register (also logs in — returns an access token, sets the refresh cookie)
curl -c cookies.txt -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"StrongPass1!","full_name":"Your Name"}'

# Call a protected endpoint with the returned access_token
curl http://localhost:8000/api/users/me -H "Authorization: Bearer <access_token>"

# Refresh (uses the cookie jar, not the access token)
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/auth/refresh

# Logout
curl -b cookies.txt -X POST http://localhost:8000/api/auth/logout
```

Or through the browser: visit http://localhost:3000, register or sign in, and you'll land on
`/dashboard`. Visiting `/dashboard` or `/admin` while signed out redirects to `/login`;
visiting `/admin` as an `EMPLOYEE` redirects back to `/dashboard` (the nav bar also only shows
the "Admin" link for `ADMIN` users).

### Seeding an admin user (development only)

There's no public way to create an admin account. For local development, set
`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` (and optionally `SEED_ADMIN_FULL_NAME`) in `.env`,
then run:

```bash
./scripts/seed-admin.sh
# or directly: docker compose exec backend python -m app.scripts.seed_admin
```

The script is a no-op if that user already exists, and refuses to run at all when
`ENVIRONMENT=production`. Never put real/production credentials in `.env`.

## Knowledge base & document ingestion

Admins upload PDF, TXT, or Markdown documents (20 MB limit by default); each one is validated
(extension + size + a magic-byte check for PDFs), stored under `backend/storage/uploads/`, and
processed through a background pipeline: extract text → clean → chunk (paragraph-aware,
~1000 tokens with ~150-token overlap by default) → generate embeddings via the **Google
Gemini** API → store chunks + embeddings in `document_chunks` (a pgvector `vector(1536)`
column with an HNSW index). A document's `status` moves through `UPLOADING` → `PROCESSING` →
`INDEXING` → `READY`, or `FAILED` with a server-side error message if any step fails.

| Method | Path | Auth required | Notes |
|---|---|---|---|
| GET | `/api/knowledge` | Bearer access token | Employees see only `READY` docs; admins see every status |
| GET | `/api/knowledge/{id}` | Bearer access token | 404 for a non-`READY` doc if the caller isn't `ADMIN` |
| POST | `/api/admin/knowledge/upload` | Bearer, `ADMIN` | Multipart form: `file`, `title`, `category`, optional `description` |
| DELETE | `/api/admin/knowledge/{id}` | Bearer, `ADMIN` | Deletes the document, its chunks, and the stored file |
| POST | `/api/admin/knowledge/{id}/reindex` | Bearer, `ADMIN` | Re-runs the pipeline on the already-stored file, bumps `version` |

The frontend's `/knowledge` page lists documents with search/category filtering (client-side —
`GET /api/knowledge` still supports `?category=`/`?search=` query params, exercised directly by
the backend tests) and polls every few seconds while any document is still processing.
`/knowledge/upload` (admin-only) has a drag-and-drop file picker; `/knowledge/{id}` shows full
document details, and — for admins — the stored `error_message` on a `FAILED` document.

**Embeddings require `GEMINI_API_KEY`** (get one at https://aistudio.google.com/apikey). Without
one, uploads still go through validation/storage/extraction/chunking correctly but fail at the
embedding step and land on `FAILED` — the same well-defined outcome a real quota/outage error
produces in production, not a crash.

### Seeding demo knowledge-base documents (optional)

Eight realistic (fictional) IT documents — VPN setup, password reset, Wi-Fi configuration,
GitHub access policy, lost/stolen laptop procedure, software installation policy, remote work
security policy, and MFA setup — are bundled for demoing the pipeline end to end:

```bash
./scripts/seed-knowledge.sh
# or directly: docker compose exec backend python -m app.scripts.seed_knowledge_base
```

Requires an admin user to already exist (`./scripts/seed-admin.sh`) and `GEMINI_API_KEY` set to
end up `READY` rather than `FAILED`. Safe to re-run — documents already present (matched by
title) are skipped.

## Architecture

See [`docs/architecture.md`](./docs/architecture.md) for the full architecture write-up and a
Mermaid diagram of the current system.

## Roadmap

This is Phase 3 of 9. Support tickets and the AI/RAG chat assistant are intentionally **not**
implemented yet — they arrive in later phases. See [`PROJECT_INFO.md`](./PROJECT_INFO.md) for
the full phase breakdown.
