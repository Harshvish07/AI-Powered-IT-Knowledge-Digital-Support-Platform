#!/usr/bin/env bash
# Development-only: creates an admin user from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD
# (set in .env). Safe to re-run — it's a no-op if the user already exists.
set -euo pipefail

docker compose exec backend python -m app.scripts.seed_admin
