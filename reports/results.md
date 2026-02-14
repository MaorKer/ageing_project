# Results

This file is intentionally lightweight. Run the pipeline to populate:
- `reports/figures/` for event-study figures
- `reports/tables/` for regression outputs and summaries

## India SRS (optional add-on)
If you have `SRS-Abridged_Life_Tables_2018-2022.pdf` in the repo root, you can extract and fit models for India + states/UTs:
```bash
python3 scripts/05_extract_srs_life_tables.py
python3 scripts/55_fit_srs_models.py
```

Key outputs:
- `data/intermediate/srs_abridged_life_tables_2018_22.csv`
- `data/processed/srs_params.parquet`
- `data/processed/srs_urban_rural_deltas.parquet`
- `reports/figures/srs/` (Urban − Rural delta plots; optional hazard overlays)

## Extra APIs (optional)
If your environment has internet access, you can fetch additional series:
```bash
python3 scripts/11_fetch_wdi_extra.py
python3 scripts/12_fetch_who_gho.py
```
