#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"${PYTHON_BIN}" -m venv .venv
source .venv/bin/activate

"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -e ".[dev]"

echo "OK: activated env at .venv. Next: source .venv/bin/activate"
