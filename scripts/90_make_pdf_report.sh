#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# Build markdown (requires Python deps; use Docker image if available).
if docker image inspect wha-py:0.1 >/dev/null 2>&1; then
  docker run --rm -v "${ROOT_DIR}":/work -w /work wha-py:0.1 bash -lc "python -m pip install -e . >/dev/null && python scripts/85_build_report_full.py"
else
  echo "Missing Docker image wha-py:0.1. Build it first:"
  echo "  docker build -f docker/Dockerfile.py -t wha-py:0.1 ."
  exit 1
fi

# Convert markdown -> PDF (pandoc/latex includes TeX).
docker run --rm -v "${ROOT_DIR}":/work -w /work pandoc/latex:latest \
  reports/report_full.md \
  -o reports/report_full.pdf \
  --resource-path=reports \
  --toc --toc-depth=2 --number-sections \
  --pdf-engine=xelatex \
  -V geometry:margin=1in

echo "Wrote reports/report_full.pdf"

