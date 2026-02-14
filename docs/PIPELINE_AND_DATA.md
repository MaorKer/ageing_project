# War & Hunger Aging Curves — Pipeline + Data Guide

This doc consolidates the repo’s purpose, the main pipeline described in `README.md`, and the additional work added in this session (SRS India life tables extraction + fitting, plus optional WDI/WHO fetchers).

## Goal (what we are modeling)

We model age-specific adult mortality hazards as a baseline exponential aging curve (Gompertz), optionally with:
- **Extrinsic mortality** (Makeham term `c`): age-independent hazard added to all adult ages.
- **Young-adult hump** (`h`): excess mortality concentrated around young-adult ages (violence signature).
- **Aging-rate changes** (`b`): changes in Gompertz slope / MRDT.

Core model code:
- Gompertz–Makeham: `src/war_hunger_aging/model/gm.py`
- Gompertz–Makeham + hump: `src/war_hunger_aging/model/gmh.py`

## What you get (main outputs)

From the **war/hunger** pipeline (see `README.md`):
- `data/processed/panel_base.parquet`: mortality + covariates at `iso3-year-sex-age`
- `data/processed/params.parquet`: fitted parameters at `iso3-year-sex`
- `reports/figures/`: event-study plots and hazard overlays
- `reports/tables/`: event summaries and regression outputs
- `reports/report.md` / `reports/report_full.md`: markdown reports

From the **SRS India (optional)** additions:
- `data/intermediate/srs_abridged_life_tables_2018_22.csv`: extracted abridged life-table rows (+ derived `mx`)
- `data/processed/srs_params.parquet`: GM/GMH fitted params per `area × residence × sex`
- `data/processed/srs_urban_rural_deltas.parquet`: Urban−Rural deltas for `b`, `c`, `h`, `mrdt`, etc.
- `reports/figures/srs/`: delta plots and optional hazard overlays
- `reports/tables/srs_params.csv`, `reports/tables/srs_urban_rural_deltas.csv`: human-readable tables

## Configuration

Main config file: `config/project.yml`
- Defines study window (`start_year`, `end_year`), sexes, ages used for fitting, hump shape defaults (`mu`, `sigma`), and case/control groups for event-study.
- Defines WDI indicator codes used in the main panel build.

Loader: `src/war_hunger_aging/config.py`

## Data sources and how they are ingested

### 1) UN WPP 2024 mortality (age-specific `mx`)
- Source: UN WPP 2024 (exported locally via R).
- Script: `scripts/30_export_wpp_from_r.R`
- Output: `data/raw/wpp_mx.csv` (and parquet if `arrow` is available in R).
- Loader: `src/war_hunger_aging/io/wpp.py`

### 2) UCDP Battle-Related Deaths (BRD)
- Source: UCDP BRD (conflict-level).
- Script (optional downloader): `scripts/15_fetch_ucdp_brd.py` (downloads a zip and extracts into `data/raw/ucdp/`).
- Script (standardizer): `scripts/20_prepare_ucdp.py`
- Output: `data/intermediate/ucdp_brd.parquet`
- Loader/standardizer: `src/war_hunger_aging/io/ucdp.py`

### 3) World Bank WDI API (core indicators used in the main panel)
This repo **does use an API** for covariates:
- Module: `src/war_hunger_aging/io/wdi.py` (HTTP calls via `requests`)
- Script: `scripts/10_fetch_wdi.py`
- Output: `data/intermediate/wdi.parquet`

The indicator codes are configured under `wdi.indicators` in `config/project.yml` (population + hunger proxies).

### 4) SRS Abridged Life Tables 2018–22 (India subnational; optional)
This is **not an API**; it’s a PDF in the repo root:
- Input: `SRS-Abridged_Life_Tables_2018-2022.pdf`
- Extractor module: `src/war_hunger_aging/io/srs_life_tables.py`
- Script: `scripts/05_extract_srs_life_tables.py`
- Output: `data/intermediate/srs_abridged_life_tables_2018_22.csv`

Extracted columns (long-form):
- `area` (India / state name as shown in PDF)
- `period` (`2018-22`)
- `residence` (`Total`, `Rural`, `Urban`)
- `sex` (`Total`, `Male`, `Female`)
- `age_interval` (`0-1`, `1-5`, `5-10`, …, `85+`)
- `nqx`, `lx`, `nLx`, `ex` (as shown in abridged tables)
- Derived: `age_mid`, `mx`

Derived hazard proxy:
- For closed intervals: $mx \\approx -\\ln(1 - nqx) / n$ (where `n` is interval width).
- For open interval `85+`: the PDF shows `nqx` as `...`, so `mx` is left missing.

### 5) Extra WDI series (life expectancy + mortality; optional)
This is an optional add-on to fetch more health/demography series from WDI:
- Script: `scripts/11_fetch_wdi_extra.py`
- Output: `data/intermediate/wdi_extra.parquet`, `data/intermediate/wdi_extra.csv`

By default it attempts:
- Life expectancy at birth: `SP.DYN.LE00.IN`, `SP.DYN.LE00.MA.IN`, `SP.DYN.LE00.FE.IN`
- Child mortality: `SP.DYN.IMRT.IN`, `SH.DYN.MORT`
- Adult mortality (coverage varies): `SP.DYN.AMRT.MA`, `SP.DYN.AMRT.FE`

### 6) WHO GHO API (optional)
This is an optional add-on to fetch WHO series via the GHO OData API:
- Module: `src/war_hunger_aging/io/who_gho.py`
- Script: `scripts/12_fetch_who_gho.py`
- Output: `data/intermediate/who_gho.parquet`, `data/intermediate/who_gho.csv`

Default indicator is set to `WHOSIS_000001` (life expectancy at birth), but you can pass `--ind` to fetch other GHO indicator codes.

## Main pipeline (war/hunger)

See `README.md` for the full quickstart; the script chain is:
1) `scripts/30_export_wpp_from_r.R`
2) `scripts/15_fetch_ucdp_brd.py` (or manual download)
3) `scripts/20_prepare_ucdp.py`
4) `scripts/10_fetch_wdi.py`
5) `scripts/40_build_panel.py`
6) `scripts/50_fit_models.py`
7) `scripts/60_make_figures.py`
8) `scripts/70_run_regressions.py`
9) `scripts/80_build_report.py` / `scripts/85_build_report_full.py`

Panel build logic: `src/war_hunger_aging/pipeline/build_panel.py`

## Optional pipeline: SRS India life-table fitting

### Step A: extract the life table into a tidy dataset
```bash
python3 scripts/05_extract_srs_life_tables.py
```

This writes the long-form table described above to `data/intermediate/`.

### Step B: fit GM/GMH and compute Urban−Rural deltas
```bash
python3 scripts/55_fit_srs_models.py
```

Outputs:
- Params per `area × residence × sex × model`:
  - `data/processed/srs_params.parquet`
  - `reports/tables/srs_params.csv`
- Urban−Rural deltas per `area × sex × model`:
  - `data/processed/srs_urban_rural_deltas.parquet`
  - `reports/tables/srs_urban_rural_deltas.csv`
- Plots:
  - `reports/figures/srs/delta_*_urban_minus_rural_*.png`

Optional hazard overlays (slower):
```bash
python3 scripts/55_fit_srs_models.py --overlay
```

### Note: abridged tables have fewer age points
To make GMH fitting usable on abridged tables, `fit_gompertz_makeham_hump` now accepts a `min_points` threshold:
- Updated function signature: `src/war_hunger_aging/model/gmh.py`
- The SRS fitting script defaults to `--min-points 12` instead of requiring 20 points.

### PDF report (Docker)
If you want a single PDF that includes the main war/hunger outputs plus the India SRS add-on (when present), run:
```bash
bash scripts/90_make_pdf_report.sh
```
This will (inside Docker) rebuild `reports/report_full.md` and then write `reports/report_full.pdf`.

## API usage (are we “using the APIs”?)

Yes, for the war/hunger pipeline:
- WDI API is used by `scripts/10_fetch_wdi.py` via `src/war_hunger_aging/io/wdi.py`.

Optional add-ons:
- WDI extra series: `scripts/11_fetch_wdi_extra.py`
- WHO GHO series: `scripts/12_fetch_who_gho.py` via `src/war_hunger_aging/io/who_gho.py`

Not an API:
- SRS abridged life tables: parsed from a local PDF.

## Environment notes

- The scripts that call WDI/WHO require **internet access**.
- If you see network/DNS failures, run the fetch scripts in an environment where outbound HTTPS and DNS resolution work.

## Next steps (if you want to extend this)

- Wire WDI extra / WHO GHO series into the main panel (`build_panel.py`) as additional covariates.
- If you want to connect SRS subnational hazards to conflict/food insecurity, you’ll need:
  - subnational covariates (state-level hunger, conflict, etc.),
  - consistent region identifiers, and
  - a modeling choice (state fixed effects, synthetic control, etc.).

### Other relevant data/APIs (not wired yet)
If you want richer outcomes/covariates beyond WPP/WDI/UCDP BRD:
- **Human Mortality Database (HMD)**: full life tables where available (requires login/API access).
- **IHME GBD**: subnational life expectancy/mortality (typically via downloads; access terms apply).
- **ACLED**: subnational conflict events (API key required).
- **UCDP GED**: subnational/geocoded conflict events (download; can pair with SRS state/UT tables).
