# Project Info

## What this is

**AI-Powered IT Knowledge & Digital Support Platform** — a portfolio-quality MVP that combines
an IT knowledge base, a support ticketing system, and an AI assistant (RAG over the knowledge
base). Document embeddings use the Google Gemini API; the chat/completions provider for the
RAG assistant itself is not yet decided (a later phase).

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

## Phase roadmap

| Phase | Name | Status |
|---|---|---|
| 1 | Project Foundation (repo structure, tooling, Docker, health check) | ✅ Done |
| 2 | Authentication & Role-Based Access Control | ✅ Done |
| 3 | Knowledge Base & Document Ingestion | ✅ Done |
| 4 | TBD | ⏳ Not started |
| 5 | TBD | ⏳ Not started |
| 6 | TBD | ⏳ Not started |
| 7 | TBD | ⏳ Not started |
| 8 | TBD | ⏳ Not started |
| 9 | TBD (planned: final polish / deployment) | ⏳ Not started |

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

## Key project files

- [`README.md`](./README.md) — setup & usage instructions
- [`docs/architecture.md`](./docs/architecture.md) — architecture write-up + Mermaid diagram
- [`howtocreate.md`](./howtocreate.md) — phase-by-phase build log (what was built and why)
- [`.env.example`](./.env.example) — environment variable template
