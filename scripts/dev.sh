#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

trap 'kill 0' EXIT

source backend/.venv/bin/activate
export PYTHONPATH="$ROOT_DIR/backend"
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload &

cd frontend
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run electron:dev &

wait
