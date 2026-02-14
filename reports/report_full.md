# War, hunger, and aging curves — Full Results

_Generated: 2026-02-14 21:50 UTC_

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

## Outputs

- **Panel (base):** `data/processed/panel_base.parquet`
- **Fitted params:** `data/processed/params.parquet`
- **Fit QC:** `data/processed/fit_qc.parquet`
- **WDI extra series (optional):** `data/intermediate/wdi_extra.parquet`
- **WHO GHO series (optional):** `data/intermediate/who_gho.parquet`
- **SRS (India) extracted table:** `data/intermediate/srs_abridged_life_tables_2018_22.csv`
- **SRS (India) fitted params:** `data/processed/srs_params.parquet`
- **SRS (India) Urban–Rural deltas:** `data/processed/srs_urban_rural_deltas.parquet`
- **SRS (India) figures:** `reports/figures/srs`
- **Figures:** `reports/figures`
- **Tables:** `reports/tables`

## India (SRS) Add-on

This repo can also fit GM/GMH on India’s SRS abridged life tables (2018–22) by `area × residence × sex`.

Run:

```bash
python3 scripts/05_extract_srs_life_tables.py
python3 scripts/55_fit_srs_models.py
```

Key outputs:

- `data/intermediate/srs_abridged_life_tables_2018_22.csv` (tidy extraction + derived `mx`)

- `data/processed/srs_params.parquet` and `reports/tables/srs_params.csv`

- `data/processed/srs_urban_rural_deltas.parquet` and `reports/tables/srs_urban_rural_deltas.csv`

- Figures: `reports/figures/srs`


### SRS Figures

![delta_b_urban_minus_rural_gm_Female](figures/srs/delta_b_urban_minus_rural_gm_Female.png)

![delta_b_urban_minus_rural_gm_Male](figures/srs/delta_b_urban_minus_rural_gm_Male.png)

![delta_b_urban_minus_rural_gm_Total](figures/srs/delta_b_urban_minus_rural_gm_Total.png)

![delta_b_urban_minus_rural_gmh_Female](figures/srs/delta_b_urban_minus_rural_gmh_Female.png)

![delta_b_urban_minus_rural_gmh_Male](figures/srs/delta_b_urban_minus_rural_gmh_Male.png)

![delta_b_urban_minus_rural_gmh_Total](figures/srs/delta_b_urban_minus_rural_gmh_Total.png)

![delta_c_urban_minus_rural_gm_Female](figures/srs/delta_c_urban_minus_rural_gm_Female.png)

![delta_c_urban_minus_rural_gm_Male](figures/srs/delta_c_urban_minus_rural_gm_Male.png)

![delta_c_urban_minus_rural_gm_Total](figures/srs/delta_c_urban_minus_rural_gm_Total.png)

![delta_c_urban_minus_rural_gmh_Female](figures/srs/delta_c_urban_minus_rural_gmh_Female.png)

![delta_c_urban_minus_rural_gmh_Male](figures/srs/delta_c_urban_minus_rural_gmh_Male.png)

![delta_c_urban_minus_rural_gmh_Total](figures/srs/delta_c_urban_minus_rural_gmh_Total.png)

![delta_cb_urban_minus_rural_gm_Female](figures/srs/delta_cb_urban_minus_rural_gm_Female.png)

![delta_cb_urban_minus_rural_gm_Male](figures/srs/delta_cb_urban_minus_rural_gm_Male.png)

![delta_cb_urban_minus_rural_gm_Total](figures/srs/delta_cb_urban_minus_rural_gm_Total.png)

![delta_cb_urban_minus_rural_gmh_Female](figures/srs/delta_cb_urban_minus_rural_gmh_Female.png)

![delta_cb_urban_minus_rural_gmh_Male](figures/srs/delta_cb_urban_minus_rural_gmh_Male.png)

![delta_cb_urban_minus_rural_gmh_Total](figures/srs/delta_cb_urban_minus_rural_gmh_Total.png)

## Fit Summary

- Fits: **680** (rows in `data/processed/params.parquet`)
- Converged: **680** (100.0%)

### Convergence Rate (sample)

| iso3 | sex | converged_rate |
| --- | --- | --- |
| BGR | Female | 1 |
| BGR | Male | 1 |
| JOR | Female | 1 |
| JOR | Male | 1 |
| MAR | Female | 1 |
| MAR | Male | 1 |
| OMN | Female | 1 |
| OMN | Male | 1 |
| POL | Female | 1 |
| POL | Male | 1 |
| ROU | Female | 1 |
| ROU | Male | 1 |
| SYR | Female | 1 |
| SYR | Male | 1 |
| TUN | Female | 1 |
| TUN | Male | 1 |
| UKR | Female | 1 |
| UKR | Male | 1 |
| YEM | Female | 1 |
| YEM | Male | 1 |

## Event-Window Summary (Cases)

| case_group | iso3 | sex | param | crisis_minus_pre |
| --- | --- | --- | --- | --- |
| SYR_2011 | SYR | Female | b | -0.004431 |
| SYR_2011 | SYR | Female | c | 0.0002054 |
| SYR_2011 | SYR | Female | h | 6.859e-05 |
| SYR_2011 | SYR | Female | mrdt | 0.2909 |
| SYR_2011 | SYR | Male | b | -0.0137 |
| SYR_2011 | SYR | Male | c | -0.0001834 |
| SYR_2011 | SYR | Male | h | 0.004174 |
| SYR_2011 | SYR | Male | mrdt | 1.035 |
| UKR_2022 | UKR | Female | b | -0.003541 |
| UKR_2022 | UKR | Female | c | 9.131e-05 |
| UKR_2022 | UKR | Female | h | -1.343e-05 |
| UKR_2022 | UKR | Female | mrdt | 0.3101 |
| UKR_2022 | UKR | Male | b | -0.01378 |
| UKR_2022 | UKR | Male | c | 8.71e-12 |
| UKR_2022 | UKR | Male | h | 0.001508 |
| UKR_2022 | UKR | Male | mrdt | 1.91 |
| YEM_2015 | YEM | Female | b | -0.0005103 |
| YEM_2015 | YEM | Female | c | -1.803e-05 |
| YEM_2015 | YEM | Female | h | -8.238e-05 |
| YEM_2015 | YEM | Female | mrdt | 0.03672 |
| YEM_2015 | YEM | Male | b | -0.005231 |
| YEM_2015 | YEM | Male | c | -0.0005862 |
| YEM_2015 | YEM | Male | h | 0.001992 |
| YEM_2015 | YEM | Male | mrdt | 0.4172 |

Full CSV: `reports/tables/event_summary.csv`

## Figures

### YEM_2015 — YEM

#### Female

![YEM_2015_YEM_Female_timeseries_b](figures/YEM_2015_YEM_Female_timeseries_b.png)

![YEM_2015_YEM_Female_timeseries_c](figures/YEM_2015_YEM_Female_timeseries_c.png)

![YEM_2015_YEM_Female_timeseries_h](figures/YEM_2015_YEM_Female_timeseries_h.png)

![YEM_2015_YEM_Female_hazard_overlays](figures/YEM_2015_YEM_Female_hazard_overlays.png)

![YEM_2015_YEM_Female_hump_component](figures/YEM_2015_YEM_Female_hump_component.png)

#### Male

![YEM_2015_YEM_Male_timeseries_b](figures/YEM_2015_YEM_Male_timeseries_b.png)

![YEM_2015_YEM_Male_timeseries_c](figures/YEM_2015_YEM_Male_timeseries_c.png)

![YEM_2015_YEM_Male_timeseries_h](figures/YEM_2015_YEM_Male_timeseries_h.png)

![YEM_2015_YEM_Male_hazard_overlays](figures/YEM_2015_YEM_Male_hazard_overlays.png)

![YEM_2015_YEM_Male_hump_component](figures/YEM_2015_YEM_Male_hump_component.png)

### SYR_2011 — SYR

#### Female

![SYR_2011_SYR_Female_timeseries_b](figures/SYR_2011_SYR_Female_timeseries_b.png)

![SYR_2011_SYR_Female_timeseries_c](figures/SYR_2011_SYR_Female_timeseries_c.png)

![SYR_2011_SYR_Female_timeseries_h](figures/SYR_2011_SYR_Female_timeseries_h.png)

![SYR_2011_SYR_Female_hazard_overlays](figures/SYR_2011_SYR_Female_hazard_overlays.png)

![SYR_2011_SYR_Female_hump_component](figures/SYR_2011_SYR_Female_hump_component.png)

#### Male

![SYR_2011_SYR_Male_timeseries_b](figures/SYR_2011_SYR_Male_timeseries_b.png)

![SYR_2011_SYR_Male_timeseries_c](figures/SYR_2011_SYR_Male_timeseries_c.png)

![SYR_2011_SYR_Male_timeseries_h](figures/SYR_2011_SYR_Male_timeseries_h.png)

![SYR_2011_SYR_Male_hazard_overlays](figures/SYR_2011_SYR_Male_hazard_overlays.png)

![SYR_2011_SYR_Male_hump_component](figures/SYR_2011_SYR_Male_hump_component.png)

### UKR_2022 — UKR

#### Female

![UKR_2022_UKR_Female_timeseries_b](figures/UKR_2022_UKR_Female_timeseries_b.png)

![UKR_2022_UKR_Female_timeseries_c](figures/UKR_2022_UKR_Female_timeseries_c.png)

![UKR_2022_UKR_Female_timeseries_h](figures/UKR_2022_UKR_Female_timeseries_h.png)

![UKR_2022_UKR_Female_hazard_overlays](figures/UKR_2022_UKR_Female_hazard_overlays.png)

![UKR_2022_UKR_Female_hump_component](figures/UKR_2022_UKR_Female_hump_component.png)

#### Male

![UKR_2022_UKR_Male_timeseries_b](figures/UKR_2022_UKR_Male_timeseries_b.png)

![UKR_2022_UKR_Male_timeseries_c](figures/UKR_2022_UKR_Male_timeseries_c.png)

![UKR_2022_UKR_Male_timeseries_h](figures/UKR_2022_UKR_Male_timeseries_h.png)

![UKR_2022_UKR_Male_hazard_overlays](figures/UKR_2022_UKR_Male_hazard_overlays.png)

![UKR_2022_UKR_Male_hump_component](figures/UKR_2022_UKR_Male_hump_component.png)

## Regressions

### Female

#### Outcome: `c`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      c   R-squared:                       0.772
Model:                            OLS   Adj. R-squared:                  0.654
Method:                 Least Squares   F-statistic:                     1.634
Date:                Thu, 05 Feb 2026   Prob (F-statistic):              0.323
Time:                        22:21:29   Log-Likelihood:                 400.40
No. Observations:                  45   AIC:                            -768.8
Df Residuals:                      29   BIC:                            -739.9
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept               9.418e-05    2.3e-05      4.103      0.000    4.92e-05       0.000
C(iso3)[T.POL]         -5.718e-05   1.35e-05     -4.226      0.000   -8.37e-05   -3.07e-05
C(iso3)[T.ROU]          7.685e-06   1.24e-05      0.619      0.536   -1.66e-05     3.2e-05
C(iso3)[T.TUN]          4.844e-05    2.6e-05      1.862      0.063   -2.55e-06    9.94e-05
C(iso3)[T.UKR]          -9.24e-05   1.51e-05     -6.112      0.000      -0.000   -6.28e-05
C(year)[T.2016]        -9.241e-06   7.51e-06     -1.231      0.218    -2.4e-05    5.47e-06
C(year)[T.2017]        -1.299e-05   1.35e-05     -0.960      0.337   -3.95e-05    1.35e-05
C(year)[T.2018]        -3.231e-05   2.55e-05     -1.266      0.205   -8.23e-05    1.77e-05
C(year)[T.2019]        -3.339e-05   2.87e-05     -1.162      0.245   -8.97e-05     2.3e-05
C(year)[T.2020]         -6.86e-05   2.04e-05     -3.362      0.001      -0.000   -2.86e-05
C(year)[T.2021]        -4.554e-05   3.11e-05     -1.464      0.143      -0.000    1.54e-05
C(year)[T.2022]        -2.297e-05   4.05e-05     -0.567      0.571      -0.000    5.65e-05
C(year)[T.2023]        -5.257e-05      3e-05     -1.752      0.080      -0.000    6.23e-06
battle_deaths_per_100k -1.563e-05   8.32e-06     -1.879      0.060   -3.19e-05    6.78e-07
pou                     1.237e-05   1.15e-05      1.080      0.280   -1.01e-05    3.48e-05
fies                    2.538e-06    2.4e-06      1.058      0.290   -2.16e-06    7.24e-06
==============================================================================
Omnibus:                        3.085   Durbin-Watson:                   2.165
Prob(Omnibus):                  0.214   Jarque-Bera (JB):                2.312
Skew:                           0.182   Prob(JB):                        0.315
Kurtosis:                       4.049   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_c_Female_coef.csv`

#### Outcome: `b`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      b   R-squared:                       0.969
Model:                            OLS   Adj. R-squared:                  0.952
Method:                 Least Squares   F-statistic:                     56.23
Date:                Thu, 05 Feb 2026   Prob (F-statistic):           0.000905
Time:                        22:21:29   Log-Likelihood:                 228.45
No. Observations:                  45   AIC:                            -424.9
Df Residuals:                      29   BIC:                            -396.0
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept                  0.1042      0.001     96.866      0.000       0.102       0.106
C(iso3)[T.POL]             0.0011      0.001      1.014      0.311      -0.001       0.003
C(iso3)[T.ROU]             0.0034      0.001      4.535      0.000       0.002       0.005
C(iso3)[T.TUN]             0.0147      0.002      7.786      0.000       0.011       0.018
C(iso3)[T.UKR]            -0.0117      0.001     -8.381      0.000      -0.014      -0.009
C(year)[T.2016]           -0.0004      0.000     -1.360      0.174      -0.001       0.000
C(year)[T.2017]           -0.0008      0.001     -1.268      0.205      -0.002       0.000
C(year)[T.2018]           -0.0011      0.001     -2.167      0.030      -0.002      -0.000
C(year)[T.2019]           -0.0007      0.001     -1.205      0.228      -0.002       0.000
C(year)[T.2020]           -0.0013      0.001     -1.228      0.220      -0.003       0.001
C(year)[T.2021]           -0.0015      0.002     -0.665      0.506      -0.006       0.003
C(year)[T.2022]           -0.0010      0.001     -1.947      0.052      -0.002    6.76e-06
C(year)[T.2023]           -0.0008      0.001     -0.702      0.483      -0.003       0.001
battle_deaths_per_100k -3.563e-05      0.000     -0.273      0.785      -0.000       0.000
pou                        0.0002      0.001      0.436      0.662      -0.001       0.001
fies                      -0.0001      0.000     -0.753      0.452      -0.000       0.000
==============================================================================
Omnibus:                       15.104   Durbin-Watson:                   1.855
Prob(Omnibus):                  0.001   Jarque-Bera (JB):               42.831
Skew:                           0.603   Prob(JB):                     5.00e-10
Kurtosis:                       7.625   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_b_Female_coef.csv`

#### Outcome: `h`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      h   R-squared:                       0.684
Model:                            OLS   Adj. R-squared:                  0.520
Method:                 Least Squares   F-statistic:                     5.096
Date:                Thu, 05 Feb 2026   Prob (F-statistic):             0.0719
Time:                        22:21:29   Log-Likelihood:                 401.28
No. Observations:                  45   AIC:                            -770.6
Df Residuals:                      29   BIC:                            -741.7
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept              -1.336e-05   2.34e-05     -0.570      0.569   -5.93e-05    3.26e-05
C(iso3)[T.POL]          7.005e-05   2.19e-05      3.199      0.001    2.71e-05       0.000
C(iso3)[T.ROU]          8.867e-07   2.07e-05      0.043      0.966   -3.97e-05    4.15e-05
C(iso3)[T.TUN]             0.0001   4.45e-05      2.259      0.024    1.33e-05       0.000
C(iso3)[T.UKR]         -1.142e-05   1.55e-05     -0.735      0.462   -4.19e-05     1.9e-05
C(year)[T.2016]         6.619e-06   2.05e-05      0.322      0.747   -3.36e-05    4.69e-05
C(year)[T.2017]         9.166e-06   1.99e-05      0.460      0.646   -2.99e-05    4.82e-05
C(year)[T.2018]         3.157e-05   4.57e-05      0.690      0.490   -5.81e-05       0.000
C(year)[T.2019]         2.733e-05    4.3e-05      0.636      0.525   -5.69e-05       0.000
C(year)[T.2020]         3.478e-05   4.92e-05      0.707      0.480   -6.16e-05       0.000
C(year)[T.2021]         1.904e-05   2.24e-05      0.851      0.395   -2.48e-05    6.29e-05
C(year)[T.2022]         3.901e-05   4.91e-05      0.795      0.427   -5.72e-05       0.000
C(year)[T.2023]         3.531e-05   4.32e-05      0.818      0.414   -4.93e-05       0.000
battle_deaths_per_100k  5.173e-05   1.52e-05      3.400      0.001    2.19e-05    8.15e-05
pou                     2.243e-06   1.71e-05      0.131      0.896   -3.12e-05    3.57e-05
fies                   -9.637e-07   4.14e-06     -0.233      0.816   -9.07e-06    7.14e-06
==============================================================================
Omnibus:                        0.386   Durbin-Watson:                   1.730
Prob(Omnibus):                  0.824   Jarque-Bera (JB):                0.074
Skew:                           0.092   Prob(JB):                        0.964
Kurtosis:                       3.074   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_h_Female_coef.csv`

### Male

#### Outcome: `c`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      c   R-squared:                       0.660
Model:                            OLS   Adj. R-squared:                  0.484
Method:                 Least Squares   F-statistic:                     14.30
Date:                Thu, 05 Feb 2026   Prob (F-statistic):             0.0123
Time:                        22:21:29   Log-Likelihood:                 379.74
No. Observations:                  45   AIC:                            -727.5
Df Residuals:                      29   BIC:                            -698.6
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept                  0.0001   3.94e-05      3.613      0.000    6.51e-05       0.000
C(iso3)[T.POL]          -8.88e-05   3.38e-05     -2.629      0.009      -0.000   -2.26e-05
C(iso3)[T.ROU]          1.051e-05   2.32e-05      0.453      0.651    -3.5e-05    5.61e-05
C(iso3)[T.TUN]             0.0001   5.41e-05      1.891      0.059   -3.75e-06       0.000
C(iso3)[T.UKR]          -4.75e-05   3.14e-05     -1.513      0.130      -0.000     1.4e-05
C(year)[T.2016]        -3.421e-05   2.91e-05     -1.178      0.239   -9.11e-05    2.27e-05
C(year)[T.2017]         1.606e-05   6.04e-05      0.266      0.790      -0.000       0.000
C(year)[T.2018]        -5.683e-05   3.92e-05     -1.448      0.148      -0.000    2.01e-05
C(year)[T.2019]        -4.194e-06   8.66e-05     -0.048      0.961      -0.000       0.000
C(year)[T.2020]        -6.852e-05   7.01e-05     -0.978      0.328      -0.000    6.88e-05
C(year)[T.2021]        -8.411e-05    7.8e-05     -1.078      0.281      -0.000    6.88e-05
C(year)[T.2022]        -6.963e-05    7.6e-05     -0.916      0.359      -0.000    7.93e-05
C(year)[T.2023]        -4.415e-06   9.04e-05     -0.049      0.961      -0.000       0.000
battle_deaths_per_100k -1.571e-05   1.69e-05     -0.928      0.353   -4.89e-05    1.75e-05
pou                    -5.572e-06   2.05e-05     -0.272      0.786   -4.58e-05    3.46e-05
fies                   -9.396e-07   5.22e-06     -0.180      0.857   -1.12e-05     9.3e-06
==============================================================================
Omnibus:                        3.559   Durbin-Watson:                   2.246
Prob(Omnibus):                  0.169   Jarque-Bera (JB):                2.953
Skew:                           0.627   Prob(JB):                        0.228
Kurtosis:                       3.018   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_c_Male_coef.csv`

#### Outcome: `b`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      b   R-squared:                       0.966
Model:                            OLS   Adj. R-squared:                  0.949
Method:                 Least Squares   F-statistic:                     14.93
Date:                Thu, 05 Feb 2026   Prob (F-statistic):             0.0113
Time:                        22:21:29   Log-Likelihood:                 215.52
No. Observations:                  45   AIC:                            -399.0
Df Residuals:                      29   BIC:                            -370.1
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept                  0.1003      0.004     28.613      0.000       0.093       0.107
C(iso3)[T.POL]            -0.0079      0.002     -3.335      0.001      -0.013      -0.003
C(iso3)[T.ROU]            -0.0013      0.001     -1.028      0.304      -0.004       0.001
C(iso3)[T.TUN]             0.0206      0.004      5.449      0.000       0.013       0.028
C(iso3)[T.UKR]            -0.0094      0.003     -2.827      0.005      -0.016      -0.003
C(year)[T.2016]           -0.0015      0.001     -1.435      0.151      -0.003       0.001
C(year)[T.2017]           -0.0015      0.001     -1.184      0.237      -0.004       0.001
C(year)[T.2018]           -0.0023      0.001     -1.564      0.118      -0.005       0.001
C(year)[T.2019]           -0.0016      0.001     -1.140      0.254      -0.004       0.001
C(year)[T.2020]            0.0007      0.002      0.339      0.735      -0.003       0.005
C(year)[T.2021]            0.0015      0.003      0.472      0.637      -0.005       0.008
C(year)[T.2022]           -0.0026      0.002     -1.491      0.136      -0.006       0.001
C(year)[T.2023]           -0.0020      0.002     -1.252      0.211      -0.005       0.001
battle_deaths_per_100k    -0.0018      0.000     -4.709      0.000      -0.002      -0.001
pou                       -0.0012      0.001     -1.668      0.095      -0.003       0.000
fies                      -0.0004      0.000     -1.101      0.271      -0.001       0.000
==============================================================================
Omnibus:                       18.038   Durbin-Watson:                   1.727
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               37.550
Skew:                           0.997   Prob(JB):                     7.02e-09
Kurtosis:                       7.006   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_b_Male_coef.csv`

#### Outcome: `h`

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      h   R-squared:                       0.832
Model:                            OLS   Adj. R-squared:                  0.746
Method:                 Least Squares   F-statistic:                     2.164
Date:                Thu, 05 Feb 2026   Prob (F-statistic):              0.237
Time:                        22:21:29   Log-Likelihood:                 329.69
No. Observations:                  45   AIC:                            -627.4
Df Residuals:                      29   BIC:                            -598.5
Df Model:                          15                                         
Covariance Type:              cluster                                         
==========================================================================================
                             coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------
Intercept                 -0.0010      0.000     -2.784      0.005      -0.002      -0.000
C(iso3)[T.POL]             0.0005      0.000      2.412      0.016    8.69e-05       0.001
C(iso3)[T.ROU]         -3.766e-05   9.79e-05     -0.385      0.700      -0.000       0.000
C(iso3)[T.TUN]             0.0004      0.000      1.463      0.144      -0.000       0.001
C(iso3)[T.UKR]            -0.0004      0.000     -1.216      0.224      -0.001       0.000
C(year)[T.2016]         2.311e-05   6.55e-05      0.353      0.724      -0.000       0.000
C(year)[T.2017]          7.49e-05   8.66e-05      0.865      0.387   -9.47e-05       0.000
C(year)[T.2018]            0.0001   8.46e-05      1.494      0.135   -3.95e-05       0.000
C(year)[T.2019]          2.59e-05   5.54e-05      0.467      0.640   -8.27e-05       0.000
C(year)[T.2020]        -4.405e-05      0.000     -0.356      0.722      -0.000       0.000
C(year)[T.2021]           -0.0001      0.000     -0.546      0.585      -0.001       0.000
C(year)[T.2022]            0.0002      0.000      1.318      0.187   -9.89e-05       0.001
C(year)[T.2023]            0.0001   8.65e-05      1.178      0.239   -6.77e-05       0.000
battle_deaths_per_100k  4.846e-05   5.68e-05      0.853      0.394   -6.29e-05       0.000
pou                        0.0002   7.89e-05      2.714      0.007    5.95e-05       0.000
fies                    3.117e-05   2.69e-05      1.159      0.246   -2.15e-05    8.39e-05
==============================================================================
Omnibus:                        8.358   Durbin-Watson:                   1.684
Prob(Omnibus):                  0.015   Jarque-Bera (JB):               16.281
Skew:                          -0.183   Prob(JB):                     0.000291
Kurtosis:                       5.924   Cond. No.                         252.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

Coefficients CSV: `reports/tables/regression_h_Male_coef.csv`


## Notes

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
