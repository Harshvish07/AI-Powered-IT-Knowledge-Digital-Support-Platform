# AI-Powered IT Knowledge & Digital Support Platform

A portfolio-quality platform combining an IT knowledge base, digital support tooling, and
AI-assisted (RAG) answers. This repository is being built in **9 phases**; this document is
kept up to date as each phase lands.

> **Current status: Phase 1 — Project Foundation.**
> Only the base architecture, tooling, and a health-check endpoint exist so far.
> No authentication, tickets, RAG, or AI features are implemented yet.

See [`PROJECT_INFO.md`](./PROJECT_INFO.md) for the phase roadmap and project-level context,
and [`howtocreate.md`](./howtocreate.md) for a running build log of what was done and why in
each phase.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL + pgvector |
| AI | OpenAI API (added in a later phase) |
| Infra | Docker, Docker Compose |
| Testing | Pytest (backend), Playwright (e2e) |

## Repository structure

```
project-root/
  frontend/            # Next.js app
    app/               # App Router pages
    components/         # Shared UI components
    features/           # Feature-scoped modules
    hooks/               # React hooks
    lib/                 # Client utilities/config
    types/               # Shared TS types
    tests/               # Playwright e2e tests
  backend/             # FastAPI app
    app/
      api/               # Route definitions
      core/              # Config, DB session
      models/            # SQLAlchemy models
      schemas/           # Pydantic schemas
      services/          # Business logic
      repositories/      # Data access
      utils/             # Helpers
      workers/           # Background jobs (future)
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

```bash
cd backend
pytest                # run tests
ruff check .          # lint
black --check .       # formatting check
```

### Frontend

```bash
cd frontend
npm run lint          # ESLint
npm run format:check  # Prettier check
npm run test:e2e      # Playwright e2e tests (requires `npx playwright install` once)
```

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

You should see `vector` listed among the installed extensions.

## Architecture

See [`docs/architecture.md`](./docs/architecture.md) for the full architecture write-up and a
Mermaid diagram of the current system.

## Roadmap

This is Phase 1 of 9. Authentication, the knowledge base, support tickets, and the AI/RAG
assistant are intentionally **not** implemented yet — they arrive in later phases. See
[`PROJECT_INFO.md`](./PROJECT_INFO.md) for the full phase breakdown.
