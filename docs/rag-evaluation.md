# RAG Evaluation

This document explains how retrieval quality for the AI Assistant (Phase 4) is measured, and
records the actual, current results of running that evaluation — not an estimate or a claim,
the real output of `scripts/evaluate-rag.sh` against the live seeded demo knowledge base at the
time this document was last updated (Phase 7, 2026-09-15).

## What this evaluates, and what it doesn't

`backend/app/scripts/evaluate_rag.py` measures **retrieval quality**: given a question, does the
system fetch the right document (or, for questions the knowledge base was never meant to
answer, does it correctly fetch nothing)? It does **not** measure whether the LLM's final
generated answer is factually correct, well-written, or complete — that would require a
separate answer-quality evaluation (LLM-graded or human-graded), which is not implemented. This
distinction matters: a perfect retrieval score says the right source material was found and
handed to the model, not that the model necessarily used it well. See "Known limitations" below.

## Evaluation set

`backend/app/evaluation/questions.json` — **27 questions** across the 10 categories requested for
this phase:

| Category | Questions | Source document |
|---|---|---|
| VPN | 2 | VPN Setup Guide |
| Wi-Fi | 2 | Wi-Fi Configuration Guide |
| password | 2 | Password Reset Procedure |
| MFA | 2 | MFA Setup Guide |
| GitHub access | 3 | GitHub Access Policy |
| software | 2 | Software Installation Policy |
| security | 3 | Remote Work Security Policy |
| remote work | 3 | Remote Work Security Policy |
| lost laptop | 3 | Laptop Lost/Stolen Procedure |
| unsupported questions | 5 | *(none — genuinely out of scope)* |

Each entry stores `question`, `expected_document` (`null` for the "unsupported questions"
category), and `expected_topic` (the category name above). "security" and "remote work" both
draw on the Remote Work Security Policy document but ask about different sections of it (device/
incident security vs. day-to-day remote-work habits) — they're kept as separate categories
because the brief asked for both, not because they're expected to be distinguishable at the
document level (this knowledge base has one document per broad topic, not one per sub-topic; see
"Known limitations").

The five "unsupported questions" (capital of France, pizza toppings, the weather, a sports
result, "the meaning of life") are deliberately unrelated to IT/company policy — the point is to
confirm the assistant recognizes when a question has nothing to do with the knowledge base at
all, not to probe a fuzzy boundary case.

## Methodology

For each question, `evaluate_rag.py` calls `rag_service.retrieve_relevant_chunks()` directly —
the exact same function the live `/api/ai/chat` endpoint calls — with **no mocking**: a real
Gemini query embedding and a real pgvector cosine-similarity search against whatever is
currently in the `document_chunks` table (the seeded demo knowledge base, in this run).

Two different measurements are taken, because the two kinds of questions need different success
criteria:

- **Answerable questions** (`expected_document` is set): retrieval is run with
  `similarity_threshold=0.0` (no filtering), so the result reflects pure ranking quality,
  independent of the app's configured `RAG_SIMILARITY_THRESHOLD`. From this:
  - **Recall@1** — the expected document is the single best-ranked match.
  - **Recall@5** — the expected document appears anywhere in the top 5.
- **Unsupported questions** (`expected_document: null`): retrieval is run with the platform's
  **real, configured** `RAG_SIMILARITY_THRESHOLD` (0.55 by default), because what actually
  matters here is whether production would trigger the safe fallback — a **correct abstention**
  means retrieval returns zero chunks at the real operating threshold.

**Overall retrieval hit rate** combines both: the fraction of *all* questions where the system
did the right thing — found the right document (Recall@5) for an answerable question, or
correctly found nothing for an unsupported one.

Run it yourself:

```bash
./scripts/evaluate-rag.sh
# or directly: docker compose exec backend python -m app.scripts.evaluate_rag
```

Requires `GEMINI_API_KEY` set and the demo knowledge base seeded
(`./scripts/seed-knowledge.sh`) — without real, indexed documents, every question would
"correctly abstain" for the wrong reason (nothing to retrieve at all), which would make the
numbers meaningless rather than good.

## Current results (2026-09-15)

Against the live seeded demo knowledge base (8 documents, one chunk each — see "Known
limitations"):

| Metric | Result |
|---|---|
| Recall@1 (22 answerable questions) | **21/22 (95.5%)** |
| Recall@5 (22 answerable questions) | **22/22 (100.0%)** |
| Correct abstention (5 unsupported questions) | **5/5 (100.0%)** |
| **Overall retrieval hit rate (27 questions)** | **27/27 (100.0%)** |

Per-category (correct / total):

| Category | Result |
|---|---|
| VPN | 2/2 |
| Wi-Fi | 2/2 |
| password | 2/2 |
| MFA | 2/2 |
| GitHub access | 3/3 |
| software | 2/2 |
| security | 3/3 |
| remote work | 3/3 |
| lost laptop | 3/3 |
| unsupported questions | 5/5 |

**The one Recall@1 miss:** "Do I need to keep full-disk encryption enabled on my company
laptop?" ranked *Laptop Lost/Stolen Procedure* first and *Remote Work Security Policy* (the
actually-expected document, which does mention full-disk encryption under "Device
requirements") second — both documents are plausibly relevant to that question, and the
expected document was still retrieved (just not ranked #1), so it counts against Recall@1 but
not Recall@5. This is arguably a reasonable ranking, not a retrieval bug — full-disk encryption
comes up naturally in both a "protect your laptop" policy and a "what to do about physical
security" policy.

## Known limitations

Read this section before treating the numbers above as a general claim about retrieval quality:

- **One chunk per document.** Every seeded demo document is short enough to fit in a single
  chunk (a known, previously-documented characteristic of the demo content since Phase 3/4).
  That means this evaluation cannot detect a failure mode that matters a great deal in a real
  deployment — retrieving the *right document* but the *wrong section/chunk* within it. A
  50-page real policy manual split into dozens of chunks would be a meaningfully harder and more
  realistic test than this one.
- **Eight, clearly-distinct documents.** With only 8 documents covering 8 non-overlapping
  topics, there's relatively little for the ranker to confuse. A production knowledge base with
  hundreds of overlapping documents (multiple VPN-related documents, several versions of a
  policy) would be a much harder discrimination problem than what's measured here.
- **The evaluator wrote the questions with full knowledge of the documents' contents.** These
  questions are not real end-user queries sampled from actual usage — they're written by someone
  who already knows exactly what each document says and phrased close to that document's own
  vocabulary. Real employees ask messier, more ambiguous, more colloquial questions ("vpn's not
  working help", "wifi password???"). This evaluation set is a reasonable regression check, not
  a proxy for real-world query difficulty.
- **Retrieval quality, not answer quality.** As stated above, a 100% Recall@5 says nothing about
  whether the LLM's generated answer, grounded in that correctly-retrieved document, is
  accurate, complete, or well-phrased. `backend/tests/test_rag.py` separately verifies grounding
  behavior (the LLM only sees retrieved chunks, never fabricates when there's no evidence) but
  does not grade answer quality against a rubric.
- **A single point-in-time run.** These are the results of one run against one snapshot of the
  seeded knowledge base and one embedding model version. They are not tracked over time (no
  regression dashboard, no CI gate on retrieval quality) — re-run `./scripts/evaluate-rag.sh`
  after any change to chunking, the embedding model, or the seed documents to get current
  numbers, rather than trusting this table indefinitely.
- **27 questions is a small evaluation set.** It's enough to sanity-check each of the 10
  requested categories and to catch a gross regression (e.g. a chunking change that stops
  producing a VPN Setup Guide chunk entirely), but it is not statistically large enough to
  support fine-grained claims like "this threshold change improves recall by 2%" — a single
  question flipping status moves the percentage by multiple points at this sample size.
