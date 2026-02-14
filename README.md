# War, Hunger, and Aging Curves — Data + Modeling Pipeline

This repo implements a fully reproducible pipeline to test whether **war** and **hunger** act like:
- added **extrinsic mortality** (`c`, Makeham term),
- a **young-adult hump** (`h`, violence signature),
- or changes in the **adult aging rate** (`b`, Gompertz slope / MRDT).

## What you get
- `data/processed/panel_base.parquet`: mortality + covariates at `iso3-year-sex-age`
- `data/processed/params.parquet`: fitted parameters at `iso3-year-sex`
- `reports/figures/`: event-study plots and hazard overlays
- `reports/tables/`: event summaries and regression outputs
- `reports/report.md`: a single markdown report that links everything
- Optional (India SRS): `data/processed/srs_params.parquet`, `data/processed/srs_urban_rural_deltas.parquet`, `reports/figures/srs/`

## Data sources (exact)
- Mortality: **UN WPP 2024** age-specific death rates (`mx`) exported via `scripts/30_export_wpp_from_r.R`
- Optional (India subnational): **SRS Abridged Life Tables 2018-22** (PDF)
  - Parsed via `scripts/05_extract_srs_life_tables.py` into `data/intermediate/srs_abridged_life_tables_2018_22.csv`
- Conflict intensity: **UCDP Battle-Related Deaths (BRD)** (manual download → standardized by `scripts/20_prepare_ucdp.py`)
- Hunger + population: **World Bank WDI API**
  - `SP.POP.TOTL` population
  - `SN.ITK.DEFC.ZS` prevalence of undernourishment (PoU)
  - `SN.ITK.MSFI.ZS` moderate or severe food insecurity (FIES)
- Optional (national add-ons):
  - **World Bank WDI API** (life expectancy + mortality): `scripts/11_fetch_wdi_extra.py`
  - **WHO GHO API** (OData): `scripts/12_fetch_who_gho.py`

## India (SRS) add-on (2018–22)
This repo can also run the same “aging curve decomposition” idea on India’s SRS abridged life tables:
- Extract the PDF into a tidy long-form table (with derived hazard proxy `mx` from `nqx`).
- Fit GM/GMH per `area × residence × sex` and compute **Urban − Rural** deltas (e.g., `Δc`, `Δb`, `Δmrdt`).
- Outputs land in `data/processed/` and `reports/figures/srs/`.

## Default study set (1990–2023)
Configured in `config/project.yml`:
- Cases: Yemen (2015–2023), Syria (2011–2023), Ukraine (2022–2023)
- Controls: region/peer controls per case group (some controls overlap; handled via a group mapping table)

## Quickstart

### 0) Create env + install
```bash
bash scripts/00_bootstrap_env.sh
source .venv/bin/activate
```

### Docker quickstart (if you don't have pip/R installed)
```bash
docker build -f docker/Dockerfile.r -t wha-r:0.1 .
docker build -f docker/Dockerfile.py -t wha-py:0.1 .

docker run --rm -v "$PWD":/work -w /work wha-r:0.1 Rscript scripts/30_export_wpp_from_r.R
docker run --rm -v "$PWD":/work -w /work wha-py:0.1 bash -lc "python scripts/15_fetch_ucdp_brd.py && python scripts/20_prepare_ucdp.py && python scripts/10_fetch_wdi.py"
docker run --rm -v "$PWD":/work -w /work wha-py:0.1 bash -lc "python scripts/40_build_panel.py && python scripts/50_fit_models.py && python scripts/60_make_figures.py && python scripts/70_run_regressions.py && python scripts/80_build_report.py"

# Optional (India SRS):
docker run --rm -v "$PWD":/work -w /work wha-py:0.1 bash -lc "python scripts/05_extract_srs_life_tables.py && python scripts/55_fit_srs_models.py"
```

### 1) Export WPP mortality (requires R)
```bash
Rscript scripts/30_export_wpp_from_r.R
```
This writes `data/raw/wpp_mx.csv` (and `data/raw/wpp_mx.parquet` if the R `arrow` package is installed).

### 2) Download UCDP BRD (manual)
Option A (recommended): download + extract automatically:
```bash
python3 scripts/15_fetch_ucdp_brd.py
```

Option B (manual):
1. Download the UCDP Battle-Related Deaths dataset (BRD) as CSV/XLSX.
2. Put the file in `data/raw/ucdp/` (create the folder if needed).

Then standardize:
```bash
python3 scripts/20_prepare_ucdp.py
```
This writes `data/intermediate/ucdp_brd.parquet`.

### 3) Fetch WDI covariates
```bash
python3 scripts/10_fetch_wdi.py
```
This writes `data/intermediate/wdi.parquet`.

### Optional: Fetch extra health/demography series (WDI / WHO)
These require internet access.
```bash
python3 scripts/11_fetch_wdi_extra.py
python3 scripts/12_fetch_who_gho.py
```

### 4) Build panel + fit models + outputs
```bash
python3 scripts/40_build_panel.py
python3 scripts/50_fit_models.py
python3 scripts/60_make_figures.py
python3 scripts/70_run_regressions.py
python3 scripts/80_build_report.py
```

### Optional: Parse SRS abridged life tables (India)
If `SRS-Abridged_Life_Tables_2018-2022.pdf` is present in the repo root:
```bash
python3 scripts/05_extract_srs_life_tables.py
```

### Optional: Fit GM/GMH on SRS life tables
Produces `data/processed/srs_params.parquet`, `data/processed/srs_urban_rural_deltas.parquet`, and plots under `reports/figures/srs/`:
```bash
python3 scripts/55_fit_srs_models.py
```

### PDF report (Docker)
```bash
bash scripts/90_make_pdf_report.sh
```
This writes `reports/report_full.pdf` (and will include the India SRS add-on if the PDF is present).

## CLI (optional)
After install, you can also use:
```bash
wha --help
```

## Notes
- You must **not commit raw data** (see `.gitignore`).
- WPP estimates in conflict zones have uncertainty; interpret `b` changes cautiously.

## Docs
- Pipeline + data details: `docs/PIPELINE_AND_DATA.md`
