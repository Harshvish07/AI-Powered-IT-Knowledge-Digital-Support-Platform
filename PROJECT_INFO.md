# Project Info

## What this is

**AI-Powered IT Knowledge & Digital Support Platform** — a portfolio-quality, **production-oriented
MVP** that combines an IT knowledge base, a support ticketing system, and an AI assistant (RAG
over the knowledge base). Both document embeddings and the RAG chat model use the Google Gemini
API. "Production-oriented" is deliberate phrasing, not "production-ready" in an absolute
sense — see [`docs/deployment.md`](./docs/deployment.md) and [`docs/testing.md`](./docs/testing.md)
for exactly what security/reliability work has and hasn't been done, and what a real production
rollout would still need.

The project is deliberately built in **9 phases**, each adding one coherent slice of
functionality on top of a clean foundation, rather than building everything at once.

## Why this structure

- Each phase is independently reviewable and demoable.
- Later phases (auth, tickets, RAG, AI) are intentionally deferred so the foundation
  (tooling, structure, Docker, DB, health check) is solid and uncluttered first.
- Keeps the codebase small, maintainable, and free of speculative/unused code at every step.

## Tech stack decisions

| Concern | Choice | Why |
|---|---|---|
| Frontend framework | Next.js (App Router) + TypeScript | Modern, file-based routing, strong TS support, industry-standard |
| Styling | Tailwind CSS | Fast iteration, no separate CSS files to maintain |
| Backend framework | FastAPI | Async-first, automatic OpenAPI docs, first-class Pydantic integration |
| ORM / migrations | SQLAlchemy + Alembic | De facto standard for Python; explicit, versioned schema changes |
| Validation | Pydantic | Native to FastAPI, used for both settings and schemas |
| Database | PostgreSQL | Reliable, relational, widely supported |
| Vector search | pgvector (Postgres extension) | Avoids a second database for embeddings; keeps RAG data colocated with relational data |
| Embeddings provider | Google Gemini API (`gemini-embedding-001`) | Switched from an originally-planned OpenAI integration when testing revealed no OpenAI billing credits were available; Gemini's embedding API supports the same 1536-dimension output via `output_dimensionality`, so no schema changes were needed. See [`howtocreate.md`](./howtocreate.md) Phase 3. |
| PDF/text extraction | `pypdf` | Pure-Python, no system dependencies (avoids heavier libraries like PyMuPDF that need compiled libs) |
| Chunk-size tokenizer | `tiktoken` (`cl100k_base`) | Widely available for approximating chunk sizes; not tied to a specific embedding provider's own tokenizer |
| Document processing | FastAPI `BackgroundTasks` | Real async status progression (UPLOADING → ... → READY/FAILED) without adding a task-queue dependency (Celery/Redis) this early |
| Containerization | Docker + Docker Compose | One command (`docker compose up`) runs the whole stack identically for any contributor |
| Backend testing | Pytest | Standard Python testing framework, integrates with FastAPI's `TestClient` |
| E2E testing | Playwright | Cross-browser, reliable, good Next.js support |
| Password hashing | Argon2 (`argon2-cffi`) | Modern, memory-hard KDF; the current OWASP-recommended default over bcrypt |
| Access tokens | JWT (`PyJWT`), short-lived (15 min) | Stateless verification on every request; short expiry limits a leaked token's blast radius |
| Refresh tokens | Opaque random token, hashed in a DB table | Lets `/api/auth/logout` actually revoke a session — a JWT-only refresh token can't be revoked before it expires |
| Rate limiting | `slowapi` | Maintained FastAPI-native wrapper around the `limits` library; avoids hand-rolling brute-force protection |
| Chat/completions provider | Google Gemini API (`gemini-3.6-flash`) | Same provider as embeddings — one API key, and avoids repeating the OpenAI billing-credit problem hit in Phase 3. See [`howtocreate.md`](./howtocreate.md) Phase 4. |
| Prompt-injection defense | Explicit system-instruction rules + `<document>`-tagged retrieval context | Retrieved chunk content can come from any uploaded file, including a malicious one — the model is told exactly what to do when document text looks like an instruction: never obey it. Verified against the live model, not just described (see Phase 4 verification). |
| Markdown rendering (chat) | `react-markdown` | LLM answers naturally come back as Markdown (bold, lists); renders it properly instead of showing literal `**`/`-` characters. Never renders raw HTML, so safe for model-generated content. |
| Structured logging | Stdlib `logging` + a small custom JSON formatter | Dependency-free (no `structlog`), sufficient at this project's scale; JSON in production for machine parsing, plain text in development for readability. See [`docs/deployment.md`](./docs/deployment.md) Phase 8. |
| Deployment target | Single-host Docker Compose (VPS) | The same Compose file as local development plus a production overlay — genuinely simple, matching this project's actual scale, per Phase 8's explicit "not enterprise infrastructure" instruction. See [`docs/deployment.md`](./docs/deployment.md). |
| Frontend production image | Next.js `output: "standalone"` | A minimal, self-contained server bundle with only used dependencies traced in — skips shipping `node_modules`/source into the production image entirely. |

## Phase roadmap

| Phase | Name | Status |
|---|---|---|
| 1 | Project Foundation (repo structure, tooling, Docker, health check) | ✅ Done |
| 2 | Authentication & Role-Based Access Control | ✅ Done |
| 3 | Knowledge Base & Document Ingestion | ✅ Done |
| 4 | RAG-Powered AI IT Assistant | ✅ Done |
| 5 | IT Support Ticketing | ✅ Done |
| 6 | Admin Dashboard & Management | ✅ Done |
| 7 | Testing, Quality & RAG Evaluation | ✅ Done |
| 8 | Production Hardening & Deployment | ✅ Done |
| 9 | TBD (planned: final polish) | ⏳ Not started |

This table is updated as each phase is defined and completed. Detailed, dated build notes for
every phase live in [`howtocreate.md`](./howtocreate.md).

## Explicitly out of scope for Phase 1

Per the Phase 1 brief, the following are **not** implemented yet, on purpose:

- Authentication / authorization
- Retrieval-Augmented Generation (RAG)
- Support ticket functionality
- Any AI/OpenAI integration beyond having the config slot (`OPENAI_API_KEY`) reserved

## Explicitly out of scope for Phase 2

Per the Phase 2 brief, the following are **not** implemented yet, on purpose:

- Any admin user-management UI beyond the read-only `GET /api/users` list (no
  create/edit/deactivate-user screens yet)
- Password reset / "forgot password" flow
- Email verification
- Multi-factor authentication
- Retrieval-Augmented Generation (RAG) and support ticket functionality (still later phases)

## Explicitly out of scope for Phase 3

Per the Phase 3 brief, the following are **not** implemented yet, on purpose:

- The AI chat interface / RAG query path itself (this phase only builds the ingestion side —
  extract, chunk, embed, store; nothing yet *reads* the embeddings for retrieval)
- Any file type beyond PDF, TXT, and Markdown (e.g. Word/`.docx`, HTML, images/OCR)
- Object storage (S3-compatible); uploaded files live on the backend's local filesystem
- A dedicated `GET /api/knowledge/categories` endpoint — the frontend derives the category
  filter's options from the currently-loaded document list instead
- Document versioning/history beyond a simple incrementing `version` counter (no diff view, no
  rollback to a previous version's chunks)
- Bulk upload or bulk delete

## Explicitly out of scope for Phase 4

Per the Phase 4 brief, the following are **not** implemented yet, on purpose:

- Support ticket functionality (still a later phase; the assistant's "no evidence" fallback
  tells the user to create a ticket, but no ticketing system exists to create one in yet)
- Streaming chat responses — implemented as reliable non-streaming request/response first, per
  the brief's own explicit guidance to prioritize correctness over streaming; see
  [`howtocreate.md`](./howtocreate.md) Phase 4 for the reasoning
- Query rewriting / conversation-aware retrieval (each turn's retrieval is based only on that
  turn's message text, not the full conversation history) — the LLM does see prior turns'
  content implicitly only in the sense that they're stored, not that they're used to re-embed
  or expand the current query
- Answer accuracy claims beyond retrieval hit rate — `scripts/evaluate-rag.sh` measures
  top-1/top-5 *retrieval* hit rate against labeled questions, not whether generated answers are
  factually correct (that would need a separate LLM-graded or human-graded answer-quality eval)
- Editing or regenerating a past assistant message

## Explicitly out of scope for Phase 5

Per the Phase 5 brief, the following are **not** implemented yet, on purpose:

- Linking a ticket to an AI Assistant conversation (e.g. "escalate this chat to a ticket") —
  the two Phase 4/5 features exist side by side but aren't wired together
- Ticket attachments (screenshots, log files)
- Email/notification alerts on ticket creation, comment, or status change
- A dedicated audit-log/history table — comments plus `created_at`/`updated_at` on the ticket
  itself serve as the timeline the brief asked for ("view ticket history"), without inventing a
  new table beyond the two the brief specified (`tickets`, `ticket_comments`)
- SLA timers, due dates, or automatic priority/status transitions
- Restricting who a ticket can be assigned to (any existing user, not just admins, can be the
  `assigned_to` — the brief didn't ask for that restriction)

## Explicitly out of scope for Phase 6

Per the Phase 6 brief, the following are **not** implemented yet, on purpose:

- Role changes (promoting an employee to admin, or vice versa) — the brief only asked for
  activate/deactivate, not role editing, so `PATCH /api/users/{id}` accepts only `is_active`
- A conversation detail/drill-in view for admins — the brief explicitly warned against exposing
  unnecessary sensitive information, and message content (real employee questions, which can
  touch on security incidents, personal account issues, etc.) is exactly that; `/admin/conversations`
  is metadata-only (title, participant, message count, timestamps) by design, with no endpoint
  that returns message content to an admin who isn't the conversation's own owner
- Server-side pagination for the dashboard's charts/tables — client-side filtering over the full
  result set (same pattern as Phases 3/5) is used throughout; the admin ticket/user/conversation
  list endpoints already accept the query params a future paginated UI would need
- A charting library dependency — the three charts are small, hand-rolled SVG/CSS components
  (a bar chart and a sparkline), deliberately avoiding a new dependency for "a small number of
  meaningful charts" (the brief's own words)
- Audit logging of admin actions (who deactivated which user, who reassigned which ticket, when)

## Explicitly out of scope for Phase 7

Per the Phase 7 brief ("do not add major new product features" — this phase is reliability and
quality work, not new functionality), the following are **not** implemented:

- A CI pipeline that runs the checks in `docs/testing.md` automatically — every check documented
  for this phase was run manually in one session; nothing currently re-runs them on every push
- A frontend unit-test framework (Jest/Vitest + React Testing Library) — critical flows are
  covered by Playwright E2E tests instead; see `docs/testing.md`'s "Known limitations"
- A dedicated CSRF token mechanism — the refresh cookie's `SameSite=Lax` attribute is a partial,
  real mitigation, documented honestly as partial rather than claimed as complete
- A Content-Security-Policy header — added instead were the three response headers that make
  sense for a JSON API with no HTML surface of its own (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`); a real CSP has nothing meaningful to scope here since
  the frontend is a separate Next.js application
- Load/performance testing — nothing in this phase measures behavior under concurrent load or at
  a data scale beyond the "large document" test's few dozen chunks
- Executing the five new Playwright E2E specs with a real browser in this session — they were
  authored and type-checked but not run, due to a documented low-disk-space constraint on the
  development machine; see `docs/testing.md`'s "End-to-end tests" section for the full,
  honest explanation and what to run to close that gap

## Explicitly out of scope for Phase 8

Per the Phase 8 brief ("the goal is not to create enterprise infrastructure"), the following are
**not** implemented:

- Kubernetes, a service mesh, or any multi-host orchestration — a single Docker Compose host is
  the deliberately-chosen "simple deployment target"
- A shared/distributed rate-limiter backend (e.g. Redis-backed `slowapi`) — the in-memory limiter
  is documented as per-process, and that limitation is stated plainly rather than solved
  prematurely for a project with no real multi-instance deployment yet
- A CI pipeline — the production checklist in `docs/deployment.md` was run manually this phase;
  nothing re-runs it automatically on every push
- Object storage (S3-compatible) for uploaded files — still local disk, as in every prior phase;
  documented as a real limitation for backup/scaling rather than fixed speculatively
- A Content-Security-Policy header, a CSRF token mechanism, or dependency-vulnerability scanning
  — each discussed honestly in `docs/deployment.md`'s "Known limitations" instead of claimed
- Minimizing Docker image size further (e.g. Alpine base images) — the current ~390 MB/~388 MB
  production images are a real improvement over the dev images (no dev tooling, no
  node_modules/source in the frontend image) but not aggressively optimized; see
  `docs/deployment.md` for why Alpine wasn't chosen for this pass
- An automated backup schedule or restore-test — `docs/deployment.md` documents the `pg_dump`
  commands and when to prefer a managed provider's built-in backups instead, not a backup
  platform

## Key project files

- [`README.md`](./README.md) — setup & usage instructions
- [`docs/architecture.md`](./docs/architecture.md) — architecture write-up + Mermaid diagram
- [`docs/testing.md`](./docs/testing.md) — testing strategy, security review, code-quality results
- [`docs/rag-evaluation.md`](./docs/rag-evaluation.md) — RAG retrieval evaluation methodology and results
- [`docs/deployment.md`](./docs/deployment.md) — deployment guide, production checklist, known limitations
- [`howtocreate.md`](./howtocreate.md) — phase-by-phase build log (what was built and why)
- [`.env.example`](./.env.example) / [`.env.production.example`](./.env.production.example) — environment variable templates
