# War & hunger vs aging curves — Report

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

## Mortality models
### Gompertz–Makeham (adult fit)
On adult ages 40–89 we fit:
\u03bc(x)=c + a e^{b x}
where:
- `b` is the aging slope (MRDT = ln(2)/b),
- `a` shifts the Gompertz component,
- `c` is an age-independent extrinsic hazard (Makeham).

### Young-adult hump extension (war signature)
To capture disproportionate young-adult violent mortality, we extend:
\u03bc(x)=c + a e^{b x} + h exp(-(x-\u03bc_h)^2/(2\sigma_h^2))
with fixed hump center/width (\u03bc_h=28, \u03c3_h=10) and estimated amplitude `h \u2265 0`.

### Estimation
We fit parameters by non-linear least squares minimizing the log-scale residual:
log(mx) - log(\u03bc(x;\u03b8))
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

## Tables

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
