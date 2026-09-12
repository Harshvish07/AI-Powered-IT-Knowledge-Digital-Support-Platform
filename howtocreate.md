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
