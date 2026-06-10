#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" - <<'PY'
import sys

if not ((3, 10) <= sys.version_info[:2] < (3, 14)):
    raise SystemExit(f"Python 3.10-3.13 is required; found {sys.version.split()[0]}")
PY

if [ ! -x backend/.venv/bin/python ]; then
  "$PYTHON_BIN" -m venv backend/.venv
fi

source backend/.venv/bin/activate
python - <<'PY'
import sys

if not ((3, 10) <= sys.version_info[:2] < (3, 14)):
    raise SystemExit(
        f"backend/.venv uses unsupported Python {sys.version.split()[0]}. "
        "Recreate it with Python 3.10-3.13."
    )
PY
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r scripts/requirements-docs.txt

deactivate

cd frontend
npm ci
cd "$ROOT_DIR"

echo "Environment is ready. Run: bash scripts/dev.sh"
