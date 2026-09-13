#!/usr/bin/env bash
# Runs the RAG retrieval evaluation harness against whatever documents are
# currently in the database (real Gemini embeddings, real pgvector search —
# no mocking). Reports top-1 / top-5 retrieval hit rates. Requires
# GEMINI_API_KEY set and the demo knowledge base seeded
# (./scripts/seed-knowledge.sh) for the bundled questions to be meaningful.
set -euo pipefail

docker compose exec backend python -m app.scripts.evaluate_rag
