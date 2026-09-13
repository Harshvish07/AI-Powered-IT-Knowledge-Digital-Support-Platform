#!/usr/bin/env bash
# Seeds the demo knowledge-base documents (see PROJECT_INFO.md). Safe to re-run
# — existing documents (matched by title) are skipped. Requires an admin user
# to already exist (./scripts/seed-admin.sh) and, for documents to end up
# READY rather than FAILED, a configured OPENAI_API_KEY in .env.
set -euo pipefail

docker compose exec backend python -m app.scripts.seed_knowledge_base
