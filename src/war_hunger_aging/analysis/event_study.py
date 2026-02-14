from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EventSummary:
    case_group: str
    iso3: str
    sex: str
    param: str
    pre_mean: float
    crisis_mean: float
    post_mean: float
    crisis_minus_pre: float


def summarize_event_windows(
    *,
    params: pd.DataFrame,
    groups: pd.DataFrame,
    param_cols: list[str],
    pre_years: int = 5,
) -> pd.DataFrame:
    """
    Build pre/crisis/post summaries per (case_group, iso3, sex, param).

    params: iso3-year-sex with parameter columns
    groups: case_group-iso3 with t0/t1/is_case_country
    """
    needed = {"iso3", "year", "sex"} | set(param_cols)
    missing = needed - set(params.columns)
    if missing:
        raise KeyError(f"params missing columns: {sorted(missing)}")

    g_needed = {"case_group", "iso3", "t0", "t1"}
    g_missing = g_needed - set(groups.columns)
    if g_missing:
        raise KeyError(f"groups missing columns: {sorted(g_missing)}")

    # Expand groups to (case_group, iso3, year) with event_time and period.
    expanded: list[dict[str, object]] = []
    for _, g in groups.iterrows():
        t0 = int(g["t0"])
        t1 = int(g["t1"])
        iso3 = str(g["iso3"])
        case_group = str(g["case_group"])
        for year in params["year"].unique():
            year_i = int(year)
            if t0 - pre_years <= year_i <= t0 - 1:
                period = "pre"
            elif t0 <= year_i <= t1:
                period = "crisis"
            elif year_i >= t1 + 1:
                period = "post"
            else:
                period = "other"
            expanded.append(
                {
                    "case_group": case_group,
                    "iso3": iso3,
                    "year": year_i,
                    "period": period,
                }
            )
    periods = pd.DataFrame(expanded)
    merged = periods.merge(params, on=["iso3", "year"], how="left")
    merged = merged.dropna(subset=["sex"])

    rows: list[EventSummary] = []
    for (case_group, iso3, sex), sdf in merged.groupby(["case_group", "iso3", "sex"]):
        for param in param_cols:
            v = sdf[["period", param]].dropna()
            if v.empty:
                continue
            means = v.groupby("period")[param].mean()
            pre = float(means.get("pre", np.nan))
            crisis = float(means.get("crisis", np.nan))
            post = float(means.get("post", np.nan))
            rows.append(
                EventSummary(
                    case_group=str(case_group),
                    iso3=str(iso3),
                    sex=str(sex),
                    param=str(param),
                    pre_mean=pre,
                    crisis_mean=crisis,
                    post_mean=post,
                    crisis_minus_pre=float(crisis - pre) if np.isfinite(crisis) and np.isfinite(pre) else np.nan,
                )
            )
    return pd.DataFrame([r.__dict__ for r in rows])

