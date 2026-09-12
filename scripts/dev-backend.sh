#!/usr/bin/env bash
# Run the backend locally (outside Docker) for fast iteration.
set -euo pipefail

cd "$(dirname "$0")/../backend"
python -m venv .venv 2>/dev/null || true
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
