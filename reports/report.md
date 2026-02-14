# War, hunger, and aging curves — Report

# Methods

## Study question
We test how **war** (conflict intensity) and **hunger** (food insecurity indicators) perturb the shape of age-specific adult mortality curves. In stable settings, adult mortality hazard increases approximately exponentially with age (Gompertz law). Crisis settings may instead add an age-independent hazard (Makeham term), introduce a young-adult “hump” (violence signature), or potentially change the adult aging slope.

## Mortality data (outcome)
We use **UN World Population Prospects (WPP) 2024** age-specific death rates (`mx`) by country, year, sex, and age. These are used as a standard approximation to the hazard within age bins.

Implementation: `scripts/30_export_wpp_from_r.R` exports `data/raw/wpp_mx.csv` (and `data/raw/wpp_mx.parquet` if the R `arrow` package is installed) with columns `iso3, year, sex, age, mx`.

## Conflict intensity (war covariate)
We use **UCDP Battle-Related Deaths (BRD)** as annual battle deaths by country-year. We aggregate battle deaths to country-year and scale by population to obtain `battle_deaths_per_100k`.

Implementation: place the downloaded BRD CSV/XLSX into `data/raw/ucdp/` and run `scripts/20_prepare_ucdp.py`.

## Hunger / food insecurity (hunger covariates)
We fetch two World Bank WDI indicators:
- `SN.ITK.DEFC.ZS`: prevalence of undernourishment (PoU, %)
- `SN.ITK.MSFI.ZS`: prevalence of moderate or severe food insecurity (FIES, %)

Population for normalization is `SP.POP.TOTL`.

Implementation: `scripts/10_fetch_wdi.py`.

## India SRS (optional add-on)
Separately from the cross-country war/hunger panel, we can apply the same “aging curve decomposition” idea to India’s **SRS Abridged Life Tables (2018–22)** at the state/UT level and by residence:
- Input: `SRS-Abridged_Life_Tables_2018-2022.pdf` (repo root)
- Extraction: `scripts/05_extract_srs_life_tables.py` → `data/intermediate/srs_abridged_life_tables_2018_22.csv`
- The abridged tables provide `nqx` over age intervals (e.g., `20–25`). We derive a hazard proxy for closed intervals:
  - $mx \\approx -\\ln(1 - nqx) / n$ (where `n` is the interval width)
  - The open-ended `85+` interval has `nqx` shown as `...` in the PDF, so `mx` is left missing.

We then fit the same GM/GMH models per `area × residence × sex` and compute **Urban − Rural** deltas:
- Fit + deltas: `scripts/55_fit_srs_models.py` → `data/processed/srs_params.parquet`, `data/processed/srs_urban_rural_deltas.parquet`, `reports/figures/srs/`, `reports/tables/srs_*.csv`

## Extra APIs (optional)
If your environment has internet access, there are optional fetchers for additional national series:
- World Bank WDI (life expectancy + mortality): `scripts/11_fetch_wdi_extra.py`
- WHO GHO (OData): `scripts/12_fetch_who_gho.py`

## Mortality models
### Gompertz–Makeham (adult fit)
On adult ages 40–89 we fit:
$\mu(x)=c + a e^{b x}$
where:
- `b` is the aging slope (MRDT = ln(2)/b),
- `a` shifts the Gompertz component,
- `c` is an age-independent extrinsic hazard (Makeham).

### Young-adult hump extension (war signature)
To capture disproportionate young-adult violent mortality, we extend:
$\mu(x)=c + a e^{b x} + h \exp\left(-\frac{(x-\mu_h)^2}{2\sigma_h^2}\right)$
with fixed hump center/width ($\mu_h=28$, $\sigma_h=10$) and estimated amplitude $h \ge 0$.

### Estimation
We fit parameters by non-linear least squares minimizing the log-scale residual:
$\log(mx) - \log(\mu(x;\theta))$
with positivity enforced by log-parameterization.

## Event windows
For each case country we define:
- pre: t0-5 … t0-1
- crisis: t0 … t1
- post: t1+1 … (if available)

Controls are selected a priori in `config/project.yml`.

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

## Figures

- reports/figures/SYR_2011_SYR_Female_hazard_overlays.png
- reports/figures/SYR_2011_SYR_Female_hump_component.png
- reports/figures/SYR_2011_SYR_Female_timeseries_b.png
- reports/figures/SYR_2011_SYR_Female_timeseries_c.png
- reports/figures/SYR_2011_SYR_Female_timeseries_h.png
- reports/figures/SYR_2011_SYR_Male_hazard_overlays.png
- reports/figures/SYR_2011_SYR_Male_hump_component.png
- reports/figures/SYR_2011_SYR_Male_timeseries_b.png
- reports/figures/SYR_2011_SYR_Male_timeseries_c.png
- reports/figures/SYR_2011_SYR_Male_timeseries_h.png
- reports/figures/UKR_2022_UKR_Female_hazard_overlays.png
- reports/figures/UKR_2022_UKR_Female_hump_component.png
- reports/figures/UKR_2022_UKR_Female_timeseries_b.png
- reports/figures/UKR_2022_UKR_Female_timeseries_c.png
- reports/figures/UKR_2022_UKR_Female_timeseries_h.png
- reports/figures/UKR_2022_UKR_Male_hazard_overlays.png
- reports/figures/UKR_2022_UKR_Male_hump_component.png
- reports/figures/UKR_2022_UKR_Male_timeseries_b.png
- reports/figures/UKR_2022_UKR_Male_timeseries_c.png
- reports/figures/UKR_2022_UKR_Male_timeseries_h.png
- reports/figures/YEM_2015_YEM_Female_hazard_overlays.png
- reports/figures/YEM_2015_YEM_Female_hump_component.png
- reports/figures/YEM_2015_YEM_Female_timeseries_b.png
- reports/figures/YEM_2015_YEM_Female_timeseries_c.png
- reports/figures/YEM_2015_YEM_Female_timeseries_h.png
- reports/figures/YEM_2015_YEM_Male_hazard_overlays.png
- reports/figures/YEM_2015_YEM_Male_hump_component.png
- reports/figures/YEM_2015_YEM_Male_timeseries_b.png
- reports/figures/YEM_2015_YEM_Male_timeseries_c.png
- reports/figures/YEM_2015_YEM_Male_timeseries_h.png
- reports/figures/srs/delta_b_urban_minus_rural_gm_Female.png
- reports/figures/srs/delta_b_urban_minus_rural_gm_Male.png
- reports/figures/srs/delta_b_urban_minus_rural_gm_Total.png
- reports/figures/srs/delta_b_urban_minus_rural_gmh_Female.png
- reports/figures/srs/delta_b_urban_minus_rural_gmh_Male.png
- reports/figures/srs/delta_b_urban_minus_rural_gmh_Total.png
- reports/figures/srs/delta_c_urban_minus_rural_gm_Female.png
- reports/figures/srs/delta_c_urban_minus_rural_gm_Male.png
- reports/figures/srs/delta_c_urban_minus_rural_gm_Total.png
- reports/figures/srs/delta_c_urban_minus_rural_gmh_Female.png
- reports/figures/srs/delta_c_urban_minus_rural_gmh_Male.png
- reports/figures/srs/delta_c_urban_minus_rural_gmh_Total.png
- reports/figures/srs/delta_cb_urban_minus_rural_gm_Female.png
- reports/figures/srs/delta_cb_urban_minus_rural_gm_Male.png
- reports/figures/srs/delta_cb_urban_minus_rural_gm_Total.png
- reports/figures/srs/delta_cb_urban_minus_rural_gmh_Female.png
- reports/figures/srs/delta_cb_urban_minus_rural_gmh_Male.png
- reports/figures/srs/delta_cb_urban_minus_rural_gmh_Total.png

## Tables

- reports/tables/event_summary.csv
- reports/tables/regression_b_Female.txt
- reports/tables/regression_b_Female_coef.csv
- reports/tables/regression_b_Male.txt
- reports/tables/regression_b_Male_coef.csv
- reports/tables/regression_c_Female.txt
- reports/tables/regression_c_Female_coef.csv
- reports/tables/regression_c_Male.txt
- reports/tables/regression_c_Male_coef.csv
- reports/tables/regression_h_Female.txt
- reports/tables/regression_h_Female_coef.csv
- reports/tables/regression_h_Male.txt
- reports/tables/regression_h_Male_coef.csv
- reports/tables/srs_params.csv
- reports/tables/srs_urban_rural_deltas.csv
