#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# Build markdown (requires Python deps; use Docker image if available).
if docker image inspect wha-py:0.1 >/dev/null 2>&1; then
  docker run --rm -v "${ROOT_DIR}":/work -w /work wha-py:0.1 bash -lc '
    set -euo pipefail

    python -m pip install -e . >/dev/null

    # Optional: include India SRS add-on if the PDF is present.
    if [ -f SRS-Abridged_Life_Tables_2018-2022.pdf ]; then
      python scripts/05_extract_srs_life_tables.py
      python scripts/55_fit_srs_models.py
    fi

    python scripts/80_build_report.py
    python scripts/85_build_report_full.py
  '
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
