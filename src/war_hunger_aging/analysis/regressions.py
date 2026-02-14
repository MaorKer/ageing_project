from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import statsmodels.formula.api as smf


@dataclass(frozen=True)
class RegressionResult:
    outcome: str
    formula: str
    n: int
    r2: float
    result: object


def run_fe_regression(
    df: pd.DataFrame,
    *,
    outcome: str,
    covariates: list[str],
    country_fe: str = "iso3",
    year_fe: str = "year",
    cluster: str = "iso3",
) -> RegressionResult:
    keep: list[str] = []
    for col in [outcome, country_fe, year_fe, *covariates, cluster]:
        if col not in keep:
            keep.append(col)
    data = df[keep].dropna().copy()
    if data.empty:
        raise ValueError("No data left after dropping NaNs for regression.")

    rhs = " + ".join(covariates + [f"C({country_fe})", f"C({year_fe})"])
    formula = f"{outcome} ~ {rhs}"
    model = smf.ols(formula, data=data)
    fitted = model.fit(cov_type="cluster", cov_kwds={"groups": data[cluster]})
    return RegressionResult(
        outcome=outcome,
        formula=formula,
        n=int(data.shape[0]),
        r2=float(getattr(fitted, "rsquared", float("nan"))),
        result=fitted,
    )
