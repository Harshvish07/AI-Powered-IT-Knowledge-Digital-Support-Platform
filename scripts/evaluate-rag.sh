#!/usr/bin/env bash
# Runs the RAG retrieval evaluation harness against whatever documents are
# currently in the database (real Gemini embeddings, real pgvector search —
# no mocking). Reports Recall@1 / Recall@5 for answerable questions plus
# correct-abstention rate for the "unsupported questions" category, and an
# overall retrieval hit rate. See docs/rag-evaluation.md. Requires
# GEMINI_API_KEY set and the demo knowledge base seeded
# (./scripts/seed-knowledge.sh) for the bundled questions to be meaningful.
set -euo pipefail

docker compose exec backend python -m app.scripts.evaluate_rag
