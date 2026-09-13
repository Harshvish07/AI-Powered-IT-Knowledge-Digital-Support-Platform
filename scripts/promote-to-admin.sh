#!/usr/bin/env bash
# Promotes an already-registered user to ADMIN. Works in every environment,
# including production — see backend/app/scripts/promote_to_admin.py.
# Usage: ./scripts/promote-to-admin.sh someone@example.com
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <email>" >&2
  exit 1
fi

docker compose exec backend python -m app.scripts.promote_to_admin "$1"
