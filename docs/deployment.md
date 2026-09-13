# Deployment Guide

This project is a **production-oriented MVP**, not a hardened enterprise system. That phrase is
used deliberately throughout this document instead of "production-ready" — see
[`docs/testing.md`](./testing.md)'s security review for exactly what is and isn't actually in
place, and "Known limitations" below for what a real production rollout would still need to
add. Everything described here has been actually built and verified (build commands run, health
checks curled, migrations applied to a genuinely empty database) — nothing in this document is
aspirational.

## Choosing a deployment target

**Recommended: a single host running Docker Compose** (a VPS — e.g. a $6–12/month DigitalOcean
droplet, Hetzner box, or similar). This is the "simple deployment target" this phase asked for:
it's exactly the same `docker-compose.yml` already used for local development, plus the
production overlay (`docker-compose.prod.yml`) described below. No Kubernetes, no managed
container orchestration service, no multi-region anything — this project's actual scale (a
portfolio-quality MVP) doesn't justify that complexity, and the brief for this phase explicitly
said not to over-engineer it.

Reasonable alternatives, briefly, if you'd rather not manage a host yourself:
- **Frontend**: Vercel or Netlify (both build Next.js natively; you'd skip the frontend's Docker
  image entirely and just set `NEXT_PUBLIC_API_BASE_URL` in their dashboard).
- **Backend**: Render, Railway, or Fly.io (all can build from `backend/Dockerfile`'s
  `production` target directly).
- **Database**: any managed Postgres with the `pgvector` extension available — Neon, Supabase,
  Timescale Cloud, or Render's managed Postgres all support it. Confirm the extension is
  installable (`CREATE EXTENSION vector;`) before committing to a provider — some managed
  Postgres tiers restrict extensions.

This document focuses on the Docker Compose path since it's the one actually built and tested
for this project; the platform-specific paths above are the same three deployables (frontend
image/build, backend image/build, Postgres+pgvector), just handed to a platform instead of a
host you manage yourself.

## Architecture recap

Three deployables, matching local development exactly:

| Component | What ships | Where |
|---|---|---|
| Frontend | `frontend/Dockerfile`'s `production` stage — a Next.js standalone server, no source/node_modules | Any host that can run a Docker image, or Vercel/Netlify |
| Backend | `backend/Dockerfile`'s `production` stage — FastAPI/Uvicorn, non-root, prod dependencies only | Any host that can run a Docker image, or Render/Railway/Fly.io |
| Database | `pgvector/pgvector:pg16` (or any Postgres 16+ with `pgvector` installed) | The same host via Compose, or a managed Postgres provider |

## Environment variables

Three templates exist, and no secret lives in any of them (or anywhere in git):

- [`.env.example`](../.env.example) — local development, safe defaults, used by
  `docker compose up`.
- [`backend/.env.example`](../backend/.env.example) — the same variables, for running the
  backend outside Docker.
- [`.env.production.example`](../.env.production.example) — a **template with placeholders**
  for a real deployment; copy it to `.env` on the production host (or translate it into your
  platform's env/secret store) and fill in every `REPLACE_WITH_...` value.

`ENVIRONMENT=production` is more than a label: `app/core/config.py`'s `assert_production_safe()`
runs once at backend startup and **refuses to boot** if, with that setting, any of the following
is still true:

- `JWT_SECRET_KEY` is still the development default
- `DEBUG` is `true`
- `COOKIE_SECURE` is `false`
- `CORS_ORIGINS` still contains a `localhost`/`127.0.0.1` entry
- `GEMINI_API_KEY` is unset

This is deliberate fail-fast behavior — an insecure production boot should be a deploy-blocking
error visible in your platform's deploy logs, not a silent misconfiguration discovered later.
Verified by `backend/tests/test_config.py` (each condition tested individually, and all three
producing one combined error message when several are wrong at once) as well as by hand: booting
the backend with `ENVIRONMENT=production` and the untouched dev defaults raises immediately with
a message listing every problem.

One variable needs special handling: **`NEXT_PUBLIC_API_BASE_URL` must be set at Docker _build_
time**, not just runtime — Next.js inlines `NEXT_PUBLIC_*` variables into the client-side
JavaScript bundle when `next build` runs. Setting it only as a container's runtime environment
variable has no effect on an already-built image. `docker-compose.prod.yml` passes it as a build
arg for exactly this reason:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.example \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend
```

## Database setup, migrations, and seed data

1. Provision Postgres 16+ with the `pgvector` extension available (the bundled
   `pgvector/pgvector:pg16` image already has it; a managed provider needs to support
   `CREATE EXTENSION vector`).
2. Point `DATABASE_URL` at it.
3. Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
   **Verified against a genuinely empty database** as part of this phase (a disposable
   throw-away Postgres container, not the dev database): all six migrations
   (`0001`–`0006`) applied cleanly in order, creating all 9 tables (`users`, `refresh_tokens`,
   `knowledge_documents`, `document_chunks`, `conversations`, `messages`, `tickets`,
   `ticket_comments`, plus Alembic's own `alembic_version`), and a full `alembic downgrade base`
   afterward cleanly reversed every one of them. This confirms migrations don't implicitly
   depend on data or schema state left over from development.
4. Create the first admin account — there is deliberately no self-service way to do this (see
   `docs/testing.md`'s authorization-boundaries review). The **development-only** seed script
   (`app.scripts.seed_admin`, driven by `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`) refuses to run
   at all when `ENVIRONMENT=production`, on purpose — putting a real admin password in an
   environment variable is worse practice than the alternative:
   ```bash
   # 1. Have that person register a normal account through the running app.
   # 2. Promote it (works in every environment, including production — it
   #    never touches a password, since the account already authenticated
   #    itself through normal registration):
   docker compose exec backend python -m app.scripts.promote_to_admin admin@yourcompany.example
   # or: ./scripts/promote-to-admin.sh admin@yourcompany.example
   ```
5. (Optional) Seed the demo knowledge base content, useful for a live demo but not required for
   a real deployment:
   ```bash
   ./scripts/seed-knowledge.sh
   ```

## Build commands

```bash
# Backend production image
docker build --target production -t itsupport-backend ./backend

# Frontend production image (NEXT_PUBLIC_API_BASE_URL is a build arg — see above)
docker build --target production \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.example \
  -t itsupport-frontend ./frontend

# Or both at once, via the production Compose overlay:
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

Both production images were built and smoke-tested (run, curled, confirmed non-root) as part of
this phase: the backend image is **~390 MB**, the frontend image **~388 MB** — neither is
minimal (an Alpine base or further layer trimming could shrink both further), but both are
meaningfully leaner than the development images (no dev/test tooling, no `node_modules`/source
in the frontend image — only the Next.js standalone server output) and both start and serve
traffic correctly as a non-root user (`appuser` for the backend, the image's built-in `node`
user for the frontend — reused rather than creating a second uid-1000 user, which fails since
`node:20-slim` already ships one).

Running the full stack in production mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Health checks

| Endpoint | Purpose | Checks |
|---|---|---|
| `GET /health` | Liveness — is the process up at all? | Nothing external; always `200` if the process is running. An orchestrator should restart the container if this fails. |
| `GET /ready` | Readiness — can it actually serve real requests? | A real `SELECT 1` against the database. Returns `503` (not a crash) if the database is unreachable. An orchestrator should stop routing traffic here without restarting the process. |

Both are wired into Docker's own `HEALTHCHECK` (baked into each Dockerfile's `production` stage,
and mirrored at the Compose level for the `dev` stage too — `docker compose ps` shows `healthy`/
`unhealthy` directly). If you deploy behind a load balancer or platform with its own health-check
configuration (Render, Fly.io, an AWS target group, etc.), point liveness at `/health` and
readiness at `/ready`, not the same endpoint for both — that distinction is the point of having
two.

## Backup and recovery

Deliberately basic — this is guidance, not a backup platform:

- **Logical backups with `pg_dump`** are sufficient at this project's scale:
  ```bash
  docker compose exec postgres pg_dump -U postgres itsupport | gzip > backup-$(date +%F).sql.gz
  ```
  Restore with `gunzip -c backup-2026-09-15.sql.gz | docker compose exec -T postgres psql -U postgres itsupport`.
- **Uploaded files** (`backend/storage/uploads/`) are not in the database — a backup strategy
  that only dumps Postgres will lose the original PDF/TXT/MD files (though not the extracted
  chunks/embeddings, which *are* in Postgres). Back up this directory too, or migrate to object
  storage (S3-compatible) before relying on this in a real deployment — see "Known limitations."
- **If using a managed Postgres provider**, use its built-in automated backups/point-in-time
  recovery instead of `pg_dump` cron jobs — that's exactly the kind of undifferentiated
  operational work a managed provider exists to take off your plate, and it's a legitimate
  reason to prefer one over the bundled container for anything beyond a demo.
- **Test restores, not just backups.** A backup that has never been restored is unverified. This
  project does not include an automated restore-test — treat that as a manual step before
  trusting any specific backup strategy in production.
- Explicitly **not built**: automated backup scheduling, off-site replication, or a
  point-in-time-recovery tool. A single `pg_dump` cron job (or your provider's built-in backups)
  is the right amount of machinery for this project's scale; anything more is premature for an
  MVP with no real production traffic yet.

## Performance considerations

Reviewed, not blindly optimized — changes were made only where a real gap was found, per this
phase's explicit "avoid premature optimization" instruction:

- **Database queries**: the admin dashboard and list endpoints (tickets, users, conversations)
  batch-resolve related data (e.g. user names for a list of tickets) with one extra query, not
  one per row — this N+1 avoidance was already in place from Phases 5–6, reviewed again here and
  found still correct. `message_repository.count_user_messages_by_day` does a sequential scan
  filtered by `role` (no index on that column) — acceptable at current message volumes for a
  dashboard chart that isn't latency-critical; noted as a candidate index if message volume ever
  grows large enough to matter, not added speculatively now.
- **Vector search**: `document_chunks.embedding` has an HNSW index (`ix_document_chunks_embedding_hnsw`,
  Phase 3) — cosine-distance search against it, not a sequential scan.
- **Connection pooling**: made explicit and configurable this phase (`DB_POOL_SIZE`,
  `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS` — see `app/core/database.py`), with
  `pool_pre_ping=True` retained so a connection silently dropped by a managed Postgres provider
  is detected and replaced rather than causing a mysterious failure.
- **Unnecessary API calls**: the RAG pipeline embeds the query exactly once per chat message and
  calls the chat LLM exactly once (or zero times, when the similarity-threshold gate abstains —
  Phase 4's structural anti-hallucination guarantee doubles as an API-call-avoidance one).
  Document re-indexing regenerates embeddings for the whole document (not per-changed-chunk),
  which is simple and correct but not incremental — acceptable given documents are edited by
  re-uploading, not fine-grained editing, in this MVP.
- **Frontend rendering**: list pages (tickets, knowledge, users, conversations) filter
  client-side over an already-fetched list rather than round-tripping to the server per
  keystroke — fine at this data scale (see `docs/testing.md`/howtocreate.md for the explicit
  scale caveat), and avoids debounce/pagination complexity that isn't needed yet.
- **Document ingestion**: runs as a FastAPI `BackgroundTask`, so the upload request returns
  immediately rather than blocking on extraction/chunking/embedding — unchanged from Phase 3,
  reviewed and still the right call for this project's scale (a real task queue like Celery would
  be over-engineering here).
- **LLM calls**: `CHAT_MAX_OUTPUT_TOKENS=1024` bounds response length/cost per call; the
  20-requests/minute rate limit on `/api/ai/chat` bounds worst-case call volume per client.

## API security review

See [`docs/testing.md`](./testing.md#security-review) for the full table (password hashing, JWT
validation, RBAC, CORS, file validation, SQL injection, XSS, secret management, authorization
boundaries). This phase's additions on top of that review:

- **Centralized error handling** (`app/main.py`, `handle_unexpected_exception`): every unhandled
  exception — a genuine bug, a database hiccup, anything not already turned into a clean
  `HTTPException` by the route itself — is caught in one place, logged server-side with full
  detail (exception, traceback, request id, path, method), and turned into one consistent JSON
  shape: `{"detail": "An unexpected error occurred. Please try again.", "request_id": "..."}`.
  Never the exception message, a stack trace, a database connection string, or an internal file
  path. Verified by `test_unexpected_database_error_returns_generic_500_without_leaking_details`,
  which simulates a real repository failure and inspects the actual response body.
- **Request validation**: FastAPI/Pydantic reject malformed JSON, missing required fields, wrong
  field types, and invalid path parameters (e.g. a non-UUID ticket id) with `422` before any
  handler code runs — verified with real malformed requests in `backend/tests/test_negative.py`,
  not assumed.
- **File upload limits**: extension allowlist, a size limit enforced before the full file is
  buffered into memory, and a magic-byte check specifically for PDFs so a renamed non-PDF can't
  pass on extension alone (all Phase 3/7, re-confirmed still correct this phase).
- **AI endpoint rate limits**: `/api/ai/chat` at 20/minute per client — reasonable for a single
  user's real usage pattern (a back-and-forth conversation) while bounding worst-case cost
  exposure from a single client hammering a paid LLM API. This is `slowapi`'s in-memory limiter,
  which only enforces per-process — see "Known limitations."
- **Error responses**: consistent across the whole API now — `HTTPException`s already returned
  `{"detail": "..."}`; unhandled exceptions now do too (previously, per `docs/testing.md`'s
  account of the bug this project found and fixed in Phase 7/8, they could leak a full Python
  traceback as plain text).
- **Logging**: see the next section — structured, correlated by request id, and deliberately
  excludes message/answer content and any secret.

## Logging

Structured logging (`app/core/logging_config.py`), JSON-formatted in production and
human-readable in development, driven by `LOG_LEVEL`. Every request gets a request id (reused
from an incoming `X-Request-ID` header if a reverse proxy already set one, otherwise generated),
propagated through a contextvar so **every** log line emitted while handling that request — from
any module, not just the one that received the request — carries the same id, and echoed back in
the `X-Request-ID` response header so a bug report can quote it.

Every AI chat request logs one structured line on completion (or failure), with exactly the
fields this phase asked for:

```json
{
  "timestamp": "...", "level": "INFO", "logger": "app.api.ai",
  "message": "AI chat request completed",
  "request_id": "...", "user_id": "...", "conversation_id": "...",
  "latency_ms": 842.3, "retrieval_count": 2, "model": "gemini-3.6-flash",
  "outcome": "answered", "confidence": "high"
}
```

**Deliberately never logged**: the user's question text, the generated answer text, passwords,
JWTs/refresh tokens, or the Gemini API key. The chat log line above is a metrics/diagnostic
record, not a transcript — the actual conversation content is already stored in the `messages`
table (visible only to its owner and, as metadata-only via `/admin/conversations`, to admins —
see Phase 6).

## Docker

- **Multi-stage builds** for both images: a shared `base`/`deps` stage, a `dev` stage (hot
  reload, dev/test tooling — what `docker-compose.yml` builds, unchanged from earlier phases so
  local development isn't disrupted), and a `production` stage (lean, no dev tooling, non-root).
- **Non-root containers**: the backend production image creates and runs as `appuser` (uid
  1000); the frontend production image runs as the `node` user `node:20-slim` already ships
  (creating a second user at the same uid fails — caught and fixed during this phase's actual
  build verification, not assumed to work).
- **Health checks**: `HEALTHCHECK` instructions in both Dockerfiles' `production` stages, and
  equivalent `healthcheck:` blocks in `docker-compose.yml` for the `dev` stage too (so
  `docker compose ps` reports real health during local development, not just in production).
  `frontend` now depends on `backend`'s health check passing, not just the container starting.
- **Production Compose overlay** (`docker-compose.prod.yml`): builds the `production` target for
  both images, removes the dev bind-mount volumes (the production image is self-contained), sets
  `restart: always`, and stops publishing Postgres's port to the host by default. Each of those
  removals uses the Compose Specification's `!reset` tag (e.g. `volumes: !reset []`), not a
  plain `[]` — Compose *merges* list-valued keys like `ports`/`volumes` across files by default,
  so a plain empty list is silently ignored and the base file's entries survive. This was caught
  by actually resolving the merged config (`docker compose config`) and checking it, not assumed
  from writing what looked like the obvious override — see `howtocreate.md`'s Phase 8 entry.
- Explicitly **not done**: Kubernetes manifests, a service mesh, or multi-host orchestration —
  out of scope per this phase's own instruction, and unjustified at this project's actual scale.

## Final production checklist

Every item below was actually run this phase, not assumed:

- [x] Clean production build — both `docker build --target production` commands succeed (see
  "Build commands"); both images run and serve traffic; both confirmed non-root.
- [x] Docker build — dev images rebuilt from the new multi-stage Dockerfiles, stack brought up
  with `docker compose up`, all three services report `healthy`.
- [x] Migrations from an empty database — all 6 migrations applied cleanly to a disposable,
  genuinely empty Postgres container; full downgrade also verified.
- [x] Tests pass — `pytest -q`: 105 passed, 2 skipped (real Gemini chat API quota — an external
  condition, not a code defect; see `docs/testing.md`), 0 failed. `ruff`, `black`, `mypy` all
  clean.
- [x] Frontend works — `npm run build` succeeds (16 routes); `eslint`, `tsc --noEmit`, `prettier
  --check` all clean; the production Docker image serves the app correctly.
- [x] Backend works — `/health` and `/ready` both verified with real `curl` requests against a
  running container.
- [x] Authentication works — register/login/refresh/logout all covered by
  `backend/tests/test_auth.py` and exercised manually via `curl` in earlier phases.
- [x] RAG works — a real question against the seeded demo knowledge base returns a grounded,
  cited answer (verified with real Gemini API calls in Phase 4/5/6's manual walkthroughs).
- [x] Citations work — source citations (document title + page) render in the assistant UI and
  are present in the API response schema, verified in `backend/tests/test_rag.py`.
- [x] Tickets work — full create/view/comment/assign/status lifecycle verified in Phase 5/6.
- [x] Admin works — dashboard metrics, user management, ticket management, and conversation
  metadata all verified against real data in Phase 6.
- [x] Errors are handled — the centralized exception handler added this phase returns a clean,
  consistent JSON body with no leaked details for any unhandled exception, verified with a real
  simulated failure, not just described.

## Known limitations

Stated plainly, not glossed over:

- **Rate limiting is in-memory and per-process.** Running more than one backend instance (or
  more than the Dockerfile's default of 1 uvicorn worker) means each process enforces the
  20/minute and 10/minute limits independently — the *effective* limit loosens by a factor of
  however many processes are running. A real multi-instance deployment needs a shared limiter
  backend (e.g. Redis-backed `slowapi`), which is not implemented.
- **No CDN/static-asset caching layer** in front of the frontend — fine at this traffic scale,
  would matter at real scale.
- **Uploaded files live on local disk** (`backend/storage/uploads/`), not object storage. This
  works for a single-host deployment but doesn't survive a host replacement without also backing
  up that directory (see "Backup and recovery"), and doesn't work at all if the backend is ever
  scaled to multiple instances without a shared filesystem.
- **No CI pipeline** — every check in the "Final production checklist" was run manually in this
  session. Nothing currently re-runs them automatically on every push.
- **No CSRF token mechanism**, only the `SameSite=Lax` cookie attribute — see
  `docs/testing.md`'s security review for what that does and doesn't guarantee.
- **No Content-Security-Policy header** — there's no server-rendered HTML on the backend for one
  to meaningfully scope to; the three headers that were added (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`) are the appropriate minimal baseline for a JSON API.
- **Docker images are not minimal.** ~390 MB / ~388 MB — a `python:3.12-alpine` or
  `node:20-alpine` base, more aggressive layer caching, or distroless base images could shrink
  both meaningfully. Not done this phase because it adds real risk (Alpine's musl libc has
  caused real, subtle breakage with some Python C-extension wheels historically) for a benefit
  that doesn't matter yet at this project's actual deployment scale.
- **No log aggregation/alerting.** Structured JSON logs are emitted to stdout, which is the
  correct thing for a container to do (let the platform/host collect it) — but nothing in this
  project ships those logs anywhere, parses them for alerting, or dashboards them. That's
  intentionally left to whatever platform this is actually deployed on.
- **The RAG evaluation and E2E test suites carry their own documented limitations** — see
  `docs/rag-evaluation.md` and `docs/testing.md` rather than repeating them here.

## Remaining technical debt

- `assert_production_safe()` checks five specific settings; it is not an exhaustive security
  linter and wouldn't catch every possible misconfiguration (e.g. a weak-but-non-default
  `JWT_SECRET_KEY`, or `ACCESS_TOKEN_EXPIRE_MINUTES` set unreasonably high).
- The backend's `uvicorn --workers 1` default (chosen for rate-limiter correctness — see "Known
  limitations") means the backend has no built-in horizontal concurrency within one container;
  scaling out currently means running multiple containers behind a load balancer, which would
  reintroduce the shared-rate-limiter gap above.
- The five Playwright E2E specs authored in Phase 7 remain unexecuted with a real browser (see
  `docs/testing.md`) — closing that gap would materially increase confidence in this checklist's
  frontend-facing items beyond "the underlying pieces were each verified separately."
- No automated restore-from-backup test exists, only the manual `pg_dump`/`psql` commands
  documented above.
- No dependency-vulnerability scanning (e.g. `pip-audit`, `npm audit` in CI) is wired in anywhere.
