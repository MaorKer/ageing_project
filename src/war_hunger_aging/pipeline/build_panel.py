from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from war_hunger_aging.config import ProjectConfig
from war_hunger_aging.io.wdi import wdi_long_to_wide


@dataclass(frozen=True)
class PanelPaths:
    panel_base: Path
    panel_event: Path
    groups: Path


def _interpolate_by_country(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.sort_values(["iso3", "year"]).copy()
    for col in cols:
        out[col] = out.groupby("iso3")[col].transform(
            lambda s: s.astype(float).interpolate(limit_area="inside")
        )
    return out


def build_panels(
    *,
    cfg: ProjectConfig,
    mortality: pd.DataFrame,
    wdi_long: pd.DataFrame,
    ucdp: pd.DataFrame,
    out_dir: Path,
) -> PanelPaths:
    """
    Writes:
    - panel_base.parquet: iso3-year-sex-age with covariates
    - panel.parquet (event): case_group-iso3-year-sex-age with event_time/period metadata
    - groups.parquet: case_group-iso3 with t0/t1/is_case
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_base_path = out_dir / "panel_base.parquet"
    panel_event_path = out_dir / "panel.parquet"
    groups_path = out_dir / "groups.parquet"

    countries = set(cfg.countries)
    mortality = mortality[
        (mortality["iso3"].isin(countries))
        & (mortality["year"] >= cfg.start_year)
        & (mortality["year"] <= cfg.end_year)
        & (mortality["sex"].isin(cfg.sexes))
        & (mortality["age"] >= cfg.fit_ages.min)
        & (mortality["age"] <= cfg.fit_ages.max)
    ].copy()
    wdi_long = wdi_long[
        (wdi_long["iso3"].isin(countries))
        & (wdi_long["year"] >= cfg.start_year)
        & (wdi_long["year"] <= cfg.end_year)
    ].copy()
    ucdp = ucdp[
        (ucdp["iso3"].isin(countries))
        & (ucdp["year"] >= cfg.start_year)
        & (ucdp["year"] <= cfg.end_year)
    ].copy()

    indicator_map = {
        cfg.wdi.indicators.population: "population",
        cfg.wdi.indicators.pou: "pou",
        cfg.wdi.indicators.fies: "fies",
    }
    wdi_wide = wdi_long_to_wide(wdi_long, indicator_map=indicator_map)

    cov = wdi_wide.merge(ucdp, on=["iso3", "year"], how="left")
    cov["battle_deaths"] = cov["battle_deaths"].fillna(0.0)

    if cfg.wdi.interpolate:
        cov = _interpolate_by_country(cov, cols=["population", "pou", "fies"])

    cov["battle_deaths_per_100k"] = np.where(
        cov["population"] > 0,
        (cov["battle_deaths"] / cov["population"]) * 100_000.0,
        np.nan,
    )

    base = mortality.merge(cov, on=["iso3", "year"], how="left")
    base["log_mx"] = np.where(base["mx"] > 0, np.log(base["mx"]), np.nan)
    base = base.sort_values(["iso3", "year", "sex", "age"]).reset_index(drop=True)

    base.to_parquet(panel_base_path, index=False)

    groups_rows: list[dict[str, object]] = []
    for group in cfg.cases:
        for iso3 in group.all_countries:
            groups_rows.append(
                {
                    "case_group": group.id,
                    "iso3": iso3,
                    "t0": group.t0,
                    "t1": group.t1,
                    "is_case_country": iso3 == group.iso3,
                }
            )
    groups = pd.DataFrame(groups_rows)
    groups.to_parquet(groups_path, index=False)

    # Expand to an event-study panel by duplicating rows per case_group.
    years = np.arange(cfg.start_year, cfg.end_year + 1, dtype=int)
    expanded_rows: list[dict[str, object]] = []
    for _, row in groups.iterrows():
        t0 = int(row["t0"])
        t1 = int(row["t1"])
        for year in years:
            if year < cfg.start_year or year > cfg.end_year:
                continue
            if year <= t0 - 1 and year >= t0 - 5:
                period = "pre"
            elif year >= t0 and year <= t1:
                period = "crisis"
            elif year >= t1 + 1:
                period = "post"
            else:
                period = "other"
            expanded_rows.append(
                {
                    "case_group": row["case_group"],
                    "iso3": row["iso3"],
                    "year": year,
                    "event_time": year - t0,
                    "period": period,
                    "t0": t0,
                    "t1": t1,
                    "is_case_country": bool(row["is_case_country"]),
                }
            )
    expanded = pd.DataFrame(expanded_rows)

    event = expanded.merge(base, on=["iso3", "year"], how="left")
    event = event.dropna(subset=["sex", "age", "mx"])
    event = event.sort_values(["case_group", "iso3", "year", "sex", "age"]).reset_index(drop=True)
    event.to_parquet(panel_event_path, index=False)

    return PanelPaths(panel_base=panel_base_path, panel_event=panel_event_path, groups=groups_path)
