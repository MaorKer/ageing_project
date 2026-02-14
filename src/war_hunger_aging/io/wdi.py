from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests


WDI_API_BASE = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class WDIRecord:
    iso3: str
    year: int
    indicator: str
    value: float | None


def _fetch_json(url: str, *, params: dict[str, str | int]) -> list:
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError(f"Unexpected WDI response shape for {resp.url}")
    return data


def fetch_indicator(
    indicator: str,
    *,
    countries: Iterable[str],
    start_year: int,
    end_year: int,
    api_base: str = WDI_API_BASE,
) -> pd.DataFrame:
    """
    Fetch a single WDI indicator for the given ISO3 country codes.

    Returns long-format: iso3, year, indicator, value.
    """
    country_str = ";".join(countries)
    url = f"{api_base}/country/{country_str}/indicator/{indicator}"
    params: dict[str, str | int] = {
        "format": "json",
        "per_page": 20000,
        "date": f"{start_year}:{end_year}",
    }

    data = _fetch_json(url, params=params)
    meta = data[0]
    pages = int(meta.get("pages", 1))

    rows: list[WDIRecord] = []
    for page in range(1, pages + 1):
        params_page = dict(params)
        params_page["page"] = page
        page_data = _fetch_json(url, params=params_page)
        observations = page_data[1]
        for obs in observations:
            if not isinstance(obs, dict):
                continue
            iso3 = obs.get("countryiso3code")
            year = obs.get("date")
            value = obs.get("value")
            if not iso3 or not year:
                continue
            try:
                year_i = int(year)
            except ValueError:
                continue
            rows.append(
                WDIRecord(
                    iso3=str(iso3).upper(),
                    year=year_i,
                    indicator=indicator,
                    value=float(value) if value is not None else None,
                )
            )

    df = pd.DataFrame([r.__dict__ for r in rows])
    if df.empty:
        return df
    return df.sort_values(["iso3", "year"]).reset_index(drop=True)


def fetch_indicators(
    indicators: Iterable[str],
    *,
    countries: Iterable[str],
    start_year: int,
    end_year: int,
    api_base: str = WDI_API_BASE,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ind in indicators:
        frames.append(
            fetch_indicator(
                ind,
                countries=countries,
                start_year=start_year,
                end_year=end_year,
                api_base=api_base,
            )
        )
    if not frames:
        return pd.DataFrame(columns=["iso3", "year", "indicator", "value"])
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values(["indicator", "iso3", "year"]).reset_index(drop=True)


def wdi_long_to_wide(
    df_long: pd.DataFrame, *, indicator_map: dict[str, str]
) -> pd.DataFrame:
    """
    Convert long-format WDI to wide columns as specified by indicator_map.
    indicator_map: {indicator_code: column_name}
    """
    df = df_long.copy()
    df = df[df["indicator"].isin(indicator_map.keys())]
    df["col"] = df["indicator"].map(indicator_map)
    wide = (
        df.pivot_table(index=["iso3", "year"], columns="col", values="value", aggfunc="first")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return wide

