# Project Info

## What this is

**AI-Powered IT Knowledge & Digital Support Platform** — a portfolio-quality MVP that combines
an IT knowledge base, a support ticketing system, and an AI assistant (RAG over the knowledge
base, powered by the OpenAI API).

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
| AI provider | OpenAI API | Used later for embeddings + chat completions in the RAG assistant |
| Containerization | Docker + Docker Compose | One command (`docker compose up`) runs the whole stack identically for any contributor |
| Backend testing | Pytest | Standard Python testing framework, integrates with FastAPI's `TestClient` |
| E2E testing | Playwright | Cross-browser, reliable, good Next.js support |

## Phase roadmap

| Phase | Name | Status |
|---|---|---|
| 1 | Project Foundation (repo structure, tooling, Docker, health check) | ✅ Done |
| 2 | TBD (planned: authentication) | ⏳ Not started |
| 3 | TBD | ⏳ Not started |
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

## Key project files

- [`README.md`](./README.md) — setup & usage instructions
- [`docs/architecture.md`](./docs/architecture.md) — architecture write-up + Mermaid diagram
- [`howtocreate.md`](./howtocreate.md) — phase-by-phase build log (what was built and why)
- [`.env.example`](./.env.example) — environment variable template
