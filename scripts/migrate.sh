#!/usr/bin/env bash
# Run Alembic migrations against the backend service.
set -euo pipefail

docker compose exec backend alembic upgrade head
