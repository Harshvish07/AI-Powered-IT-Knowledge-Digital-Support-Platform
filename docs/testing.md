# Testing, Quality & Security — Phase 7

This document explains the testing strategy across the platform, records what was actually run
and what it found (including one real bug this phase's own testing effort uncovered and fixed),
and gives an honest assessment of what's still weak. See also
[`docs/rag-evaluation.md`](./rag-evaluation.md) for the RAG-specific evaluation methodology and
results, which this document only summarizes.

## Testing strategy

Three layers, each targeting a different kind of defect:

1. **Backend unit/integration tests (Pytest)** — the largest and most trustworthy layer. Every
   route, repository, and service function that matters is exercised against a **real
   PostgreSQL database** (each test runs inside a transaction that's rolled back afterward — see
   `backend/tests/conftest.py` — never SQLite or an in-memory fake), with external paid APIs
   (Gemini embeddings/chat) mocked by default and a small number of tests that call the **real**
   API, gated on `GEMINI_API_KEY` being configured and skipping (not failing) if the API is
   genuinely unavailable (e.g. free-tier quota exhaustion — a real, previously-encountered
   condition, not a hypothetical).
2. **End-to-end tests (Playwright)** — real browser, real frontend dev server, real backend, real
   database, exercising the five flows the phase specified. See "End-to-end tests" below for an
   important, honestly-stated caveat about what was and wasn't actually run this phase.
3. **Manual verification** — for anything the automated layers can't cheaply cover (e.g.
   Docker Compose behavior, visual review of the dashboard/charts), performed and recorded in
   `howtocreate.md`'s per-phase verification tables since Phase 1.

There is no separate frontend unit-test framework (Jest/Vitest + React Testing Library) in this
project — "frontend testing" for the critical flows listed in this phase's brief is covered by
the Playwright E2E layer instead, which exercises the same components through real user
interactions rather than in isolation. This is a deliberate scope choice, not an oversight — see
"Known limitations" for the tradeoff.

## Backend test architecture

`backend/tests/`, one file per domain area, following the same shape throughout: small
`_create_user`/`_login`/`_admin_headers`/`_employee_headers` helpers local to each file (not
shared via a central fixture module, so each file stays readable on its own), a `client` fixture
(FastAPI `TestClient` wired to the transactional `db_session`), and `unique_email()` from
`conftest.py` so parallel/repeated runs never collide on a unique constraint.

| File | Covers | Tests |
|---|---|---|
| `test_health.py` | Liveness endpoint | 1 |
| `test_auth.py` | Registration, login, JWT issuance/validation/expiry, refresh/rotation, logout, RBAC | 16 |
| `test_knowledge.py` | Upload validation, text extraction, chunking, embedding persistence, ingestion pipeline status transitions, search/filter, admin-only actions, **corrupted PDFs, empty documents, oversized/large documents** (Phase 7 additions) | 24 |
| `test_rag.py` | Retrieval (real pgvector queries via hand-constructed embeddings), grounded answers, the no-evidence fallback, confidence scoring, conversation persistence/ownership, prompt-injection defense (structural + real-API), LLM/embedding failure handling | 12 |
| `test_tickets.py` | Ticket CRUD, validation, ownership visibility, comments, admin assignment/status/priority updates, RBAC | 18 |
| `test_admin.py` | Dashboard metrics (against real seeded data), admin ticket filters, user search/role-filter/activate-deactivate/self-lockout, admin conversation metadata (and that it excludes message content) | 14 |
| `test_negative.py` (Phase 7) | Rate limiting, malformed JSON/fields/UUIDs, SQL-injection-shaped input, simulated database failure | 8 |

**97 tests collected**, of which 2 are real-API integration tests (`test_rag.py`) that
skip gracefully rather than fail when the Gemini free-tier quota is exhausted — this is a
property of testing against a live, rate-limited third party, not a flaw in the tests. A run at
the time of writing this document: **95 passed, 2 skipped, 0 failed** (`pytest -q`, inside the
Docker backend container). Re-running when the quota resets typically shows all 97 passing — see
`howtocreate.md`'s Phase 4 entry for the earlier occurrence of the same, already-understood
condition.

### What Phase 7 added to backend coverage

The brief asked for strong coverage across a specific list of areas. Most of it (auth,
authorization, users, documents, ingestion, chunking, embeddings, vector search, RAG,
conversations, tickets, comments, admin APIs) was already covered by Phases 2–6's own test
suites, written alongside each feature. This phase's job was to find and close the *gaps*:

- **Corrupted PDFs** (`test_upload_corrupted_pdf_rejected`) — a `.pdf`-named file with non-PDF
  bytes must be rejected at upload time by the magic-byte check, not merely fail later.
- **Empty documents** (`test_empty_document_marks_failed_with_clear_error`) — a supported file
  type with no extractable text must fail cleanly (`FAILED` + a clear error), not crash or
  produce a phantom `READY` document with zero chunks.
- **Large documents** (`test_large_document_chunks_and_indexes_successfully`) — a document big
  enough to produce dozens of chunks (not the usual handful) must still process correctly end to
  end.
- **Rate limiting** (`test_login_is_rate_limited_after_repeated_attempts`) — the auth endpoints'
  10/minute cap actually returns `429` on the 11th attempt, not just configured and unused.
- **Malformed requests** (three tests) — genuinely unparseable JSON, missing required fields,
  wrong field types, and an invalid UUID in a path parameter all return `422`, never `500`.
- **SQL-injection-shaped input** (two tests) — search/filter query params and a login email
  containing injection-shaped strings (`'; DROP TABLE tickets; --`, `' OR '1'='1`) are proven, by
  observed behavior, to be treated as ordinary literal values: a 200 response, no error, and a
  known row confirmed to still exist in the database afterward. This isn't a guess about
  SQLAlchemy's safety — it's a direct check.
- **Simulated database failure** (`test_unexpected_database_error_returns_generic_500_without_leaking_details`)
  — monkeypatches a repository function to raise, then asserts the response is a generic `500`
  that contains neither the exception message nor a traceback. **This test caught a real bug**:
  see "A bug this phase found and fixed" below.

Negative-path coverage this phase did **not** need to add, because it already existed:
prompt injection (structural + real-API, `test_rag.py`), malicious prompts (the same real-API
test), LLM API failure and embedding API failure (`test_rag.py`, `test_knowledge.py`), invalid
and expired tokens (`test_auth.py`), and unauthorized API access (every domain file has 401/403
tests for its own endpoints).

## A bug this phase found and fixed

Writing `test_unexpected_database_error_returns_generic_500_without_leaking_details` surfaced a
real issue: `Settings.debug` defaulted to `True`, and both `.env.example` files shipped
`DEBUG=true` — but the FastAPI app was never actually constructed with `debug=settings.debug` in
the first place, so the setting was silent dead code. The very first version of this test failed
with the full Python traceback (including the simulated exception's message) appearing verbatim
in the HTTP response body, once the app was wired to actually respect the setting.

Fixed by: changing `Settings.debug` to default to `False`; wiring
`FastAPI(title=settings.app_name, debug=settings.debug)` in `app/main.py`; and changing `DEBUG`
to `false` in all four env templates/files (`.env`, `.env.example`, `backend/.env`,
`backend/.env.example`). The test now passes because the behavior it checks is real, not because
the assertion was written to match whatever the app already did.

This is exactly the class of bug integration testing is supposed to catch — a setting that
*looked* like it did something and didn't — and it's called out explicitly here rather than
glossed over, per this phase's own instruction not to claim a security property unless it
actually exists.

## End-to-end tests (Playwright)

`frontend/tests/`, one spec file per area, using real registration/login (no mocked auth) against
a real running backend + database, consistent with the existing `auth.spec.ts`/`dashboard.spec.ts`
from earlier phases.

| File | Covers |
|---|---|
| `auth.spec.ts` (existing) | Registration → dashboard, logout, login, wrong-password error — Flow 1 |
| `assistant.spec.ts` (Phase 7) | Flow 2 (known question → grounded answer → source citation) and Flow 3 (unknown question → safe fallback) |
| `tickets.spec.ts` (Phase 7) | Flow 4 (create ticket → view detail), plus client-side validation and posting a comment |
| `admin.spec.ts` (Phase 7) | Flow 5 (admin login → dashboard → view ticket → assign → change status) |
| `knowledge.spec.ts` (Phase 7) | Knowledge base search (upload a uniquely-titled document, confirm it's findable by search and that an unrelated search finds nothing) |

Mapping onto the "frontend testing" checklist: registration, login, and logout are covered by
`auth.spec.ts`; the AI assistant and source citations by `assistant.spec.ts`; knowledge base
search by `knowledge.spec.ts`; ticket creation and details by `tickets.spec.ts`; the admin
dashboard by `admin.spec.ts`.

**Two of the five specs require environment preconditions beyond "the stack is running":**

- `assistant.spec.ts`'s known-question test and `knowledge.spec.ts` need `GEMINI_API_KEY`
  configured in the backend (real embeddings, and for the assistant test, a real chat
  completion). The known-question test additionally needs the demo knowledge base seeded
  (`./scripts/seed-knowledge.sh`) so there's a real "MFA Setup Guide" document to find.
- `admin.spec.ts` and `knowledge.spec.ts` need a seeded `ADMIN` account (there is no self-service
  way to create one, by design), supplied via `E2E_ADMIN_EMAIL`/`E2E_ADMIN_PASSWORD` environment
  variables when running `npm run test:e2e`.

Both specs are written to **skip with a clear message**, not fail, when these preconditions
aren't met or when the real Gemini chat API is rate-limited — the same "distinguish environment
unavailability from a code defect" philosophy already established for the backend's real-API
tests in Phase 4.

### Honest note on execution

The four new Phase 7 spec files were authored carefully against the actual rendered DOM/text of
each page (cross-checked directly against the component source, not guessed), and the whole
`frontend/tests/` directory — new and existing — passes `tsc --noEmit` and `eslint` with zero
errors. **They were not executed with a real browser in this session.** The development machine
this phase was completed on had well under 2 GB of free disk space at the time (a pre-existing,
documented constraint — see the project's zombie-Chrome-process memory note from an earlier
session), and launching Playwright's Chromium on a nearly-full disk risked destabilizing the
whole machine, not just failing a test. Rather than either skip this section silently or falsely
claim a passing run, this is stated plainly: **run `npm run test:e2e` (with
`E2E_ADMIN_EMAIL`/`E2E_ADMIN_PASSWORD` set, backend + Postgres running, migrations applied) to
get a real result**, and treat these five specs as authored-and-type-checked, not
execution-verified, until that's done. This is a real limitation of this phase's verification,
not a detail to gloss over — see "Known limitations."

## RAG evaluation

Summarized here; full methodology and results in [`docs/rag-evaluation.md`](./rag-evaluation.md).
27 questions across the 10 requested categories (VPN, Wi-Fi, password, MFA, GitHub access,
software, security, remote work, lost laptop, unsupported questions). Current results against
the live seeded demo knowledge base: **Recall@1 95.5%, Recall@5 100%, correct abstention on
unsupported questions 100%, overall retrieval hit rate 100%** — with an honest discussion of why
a small, curator-written evaluation set over 8 short, topically-distinct documents shouldn't be
read as a general claim about retrieval quality at real-world scale.

## Security review

Each item below was actually checked against the running code — not asserted from memory of
having built it — per this phase's explicit instruction not to claim a security property unless
it's real.

| Area | Status | Detail |
|---|---|---|
| Password hashing | ✅ Real | Argon2 (`argon2-cffi`) via `core/security.py`; never stores or logs plaintext passwords. |
| JWT validation | ✅ Real | `jwt.decode(..., algorithms=[settings.jwt_algorithm])` explicitly pins the accepted algorithm (defends against the classic "alg" confusion/`none` attack); expiry is checked and raises a typed `InvalidTokenError`; `test_expired_token`/`test_invalid_token` verify this against the real JWT library, not a mock. |
| RBAC | ✅ Real | `require_admin`/`require_authenticated_user` (`api/deps.py`) gate every admin route at the dependency level — verified in every domain test file, not just documented; ownership checks (tickets, conversations) return 404 rather than 403 for another user's resource, so existence isn't leaked either. |
| CORS | ✅ Configured, narrow by default | `cors_origins` defaults to a single explicit origin (`http://localhost:3000`), required (not a wildcard) because `allow_credentials=True` is set — a wildcard origin with credentials is rejected by browsers anyway, so this is enforced by the platform, not just convention. |
| Rate limiting | ⚠️ Real but limited | `slowapi`, in-memory: auth endpoints at 10/minute (verified by `test_login_is_rate_limited_after_repeated_attempts` — a real 429 after 10 attempts), the AI chat endpoint at 20/minute. **Limitation**: in-memory state means limits are per-process and reset on restart — a multi-instance production deployment would need a shared backend (e.g. Redis) for this to hold across instances. Documented, not hidden. |
| File validation | ✅ Real | Extension allowlist, size limit enforced *before* the full file is buffered (reads at most `limit+1` bytes), and a magic-byte check specifically for PDFs (`test_upload_corrupted_pdf_rejected`) so a renamed non-PDF can't slip through on extension alone. |
| SQL injection | ✅ Real, verified | Every query goes through SQLAlchemy's Core/ORM query builder — no raw string-interpolated SQL anywhere in the codebase. `test_negative.py` doesn't just assert this by code inspection; it sends actual injection-shaped payloads through search/filter params and a login field and confirms normal behavior plus data integrity afterward. |
| XSS | ✅ Real, by construction | No `dangerouslySetInnerHTML` anywhere in the frontend (verified by search, not assumed) — React escapes all rendered text by default. The one place untrusted, LLM-generated Markdown is rendered (`MessageBubble.tsx`) uses `react-markdown`, which never renders raw HTML even if the model's output contained an HTML/script tag. |
| Secret management | ✅ Real | `.env`/`.env.local` gitignored; every default secret (`JWT_SECRET_KEY`, admin seed credentials) is clearly labeled dev-only/insecure in the template files; secrets are never printed to terminal output or logged (checked throughout this project's history, including when handling the Gemini API key). |
| Authorization boundaries | ✅ Real | Beyond RBAC: admins can't deactivate their own account (`400`, checked before any write — `test_admin_cannot_deactivate_own_account`); the admin conversation-metadata endpoint has no code path that fetches message content at all, so there's nothing to leak by omission-mistake later. |
| Unhandled-exception disclosure | ✅ Fixed this phase | See "A bug this phase found and fixed" above — `DEBUG` now genuinely defaults to `false` everywhere, and is verified (not assumed) by a test that triggers a real unhandled exception and inspects the response body. |
| Security response headers | ✅ Added this phase | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` on every response (`app/main.py`). This is a minimal baseline appropriate for a JSON API with no HTML surface of its own — not a substitute for a real Content-Security-Policy, which wasn't added because there's no server-rendered HTML for it to meaningfully scope (the frontend is a separate Next.js app). |
| CSRF | ⚠️ Partial, by cookie attribute only | The refresh-token cookie is `SameSite=Lax` and scoped to `/api/auth`, which blocks the classic cross-site form-POST CSRF pattern for that cookie in modern browsers. There is no CSRF token mechanism. This is a reasonable, common modern default (SameSite cookies are why explicit CSRF tokens have become less universal), but it is **not** the same guarantee a dedicated CSRF token gives, and it's listed here as a partial measure rather than a solved problem. |

## Code quality

Run and passing at the time of writing:

| Check | Result |
|---|---|
| `ruff check .` (backend) | ✅ Clean |
| `black --check .` (backend) | ✅ Clean |
| `mypy app` (backend) | ✅ Clean, 58 source files |
| `pytest -q` (backend) | ✅ 95 passed, 2 skipped (real-API quota — see above), 0 failed |
| `eslint` (frontend, all of `app/`, `features/`, `components/`, `tests/`) | ✅ Clean |
| `tsc --noEmit` (frontend) | ✅ Clean |
| `prettier --check .` (frontend) | ✅ Clean |
| `npm run build` (frontend, Turbopack production build) | ✅ All 16 routes compile |
| `docker compose` (postgres, backend, frontend) | ✅ All three healthy throughout this phase's work |

No lint rule was disabled or suppressed to make any of the above pass. The one accessibility gap
found along the way (see below) was fixed at the source rather than worked around.

### A small accessibility/testability fix made along the way

While writing `admin.spec.ts`, the admin ticket-management `<select>` elements for status,
priority, and assignment turned out to have `<label>` text but no `htmlFor`/`id` association —
meaning a screen reader (and Playwright's `getByLabel`) couldn't reliably connect the label to
its control. Fixed in `features/tickets/AdminTicketControls.tsx` by adding matching
`id`/`htmlFor` pairs — a real accessibility improvement that also happened to be exactly what was
needed for a reliable E2E selector, rather than reaching for a test-only `data-testid` workaround.

## Known limitations (honest assessment)

This phase's own instruction was not to claim more than what was actually verified. In that
spirit:

- **The five new Playwright specs are authored and type-checked, not execution-verified**, for
  the disk-space reason explained above. This is the single biggest gap in this phase's
  verification and should be closed by running `npm run test:e2e` in an environment with normal
  disk headroom before treating them as trustworthy regression coverage.
- **No frontend unit-test layer.** Component logic (hooks, form validation, badge rendering) is
  only exercised indirectly through Playwright, never in isolation. A hook with a subtle bug in
  an edge case a Playwright flow doesn't happen to trigger could go unnoticed longer than it
  would with dedicated unit tests.
- **Rate limiting is in-memory and per-process** (see the security review table) — fine for this
  project's current single-instance deployment, not sufficient for a horizontally-scaled one.
- **CSRF protection is `SameSite=Lax` only**, not a dedicated token scheme — see the security
  review table for what that does and doesn't guarantee.
- **The RAG evaluation set is small (27 questions) and curator-written**, not sampled from real
  user behavior — see `docs/rag-evaluation.md`'s own "Known limitations" for the full discussion
  of what a 100% score here does and doesn't prove.
- **No load/performance testing of any kind.** Nothing in this phase measures how the platform
  behaves under concurrent load, large datasets beyond the "large document" test's few dozen
  chunks, or sustained traffic. All performance-related claims in earlier phases' documentation
  are about algorithmic choices (e.g. avoiding N+1 queries), not measured throughput.
- **No CI pipeline.** All of the checks in "Code quality" above were run manually in this
  session; nothing currently re-runs them automatically on every push. A regression introduced
  after this phase would only be caught by someone remembering to run the same commands again.
- **The database-failure test simulates only one failure mode** (a repository function raising a
  generic exception) at one endpoint. It demonstrates the *pattern* (unhandled exceptions don't
  leak details, thanks to the `DEBUG` fix) but doesn't exercise real infrastructure failures like
  a dropped connection pool, a replica failover, or a slow query timing out.
