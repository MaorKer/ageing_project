from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd
import requests


GHO_API_BASE = "https://ghoapi.azureedge.net/api"


@dataclass(frozen=True)
class GHORecord:
    indicator: str
    spatial: str | None
    time: int | None
    value: float | None
    raw: dict[str, Any]


def _get_json(url: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected WHO GHO response shape for {resp.url}")
    return data


def fetch_gho_indicator(
    indicator: str,
    *,
    api_base: str = GHO_API_BASE,
    select: Iterable[str] | None = None,
    where: str | None = None,
) -> pd.DataFrame:
    """
    Fetch a WHO GHO indicator table via the public OData API.

    The API serves data at:
      {api_base}/{indicator}
    and paginates using '@odata.nextLink'.

    Returns a long-format DataFrame with best-effort normalized columns:
      indicator, iso3, year, value, plus raw fields.
    """
    url = f"{api_base.rstrip('/')}/{indicator}"

    params: dict[str, str] = {}
    if select:
        params["$select"] = ",".join(select)
    if where:
        params["$filter"] = where

    rows: list[GHORecord] = []
    next_url: str | None = url
    next_params: dict[str, str] | None = params or None

    while next_url is not None:
        data = _get_json(next_url, params=next_params)
        values = data.get("value")
        if not isinstance(values, list):
            raise ValueError(f"Missing 'value' array in WHO GHO response for {next_url}")

        for obs in values:
            if not isinstance(obs, dict):
                continue
            spatial = obs.get("SpatialDim") or obs.get("SpatialDimValueCode") or obs.get("COUNTRY")
            time = obs.get("TimeDim") or obs.get("YEAR")
            numeric = obs.get("NumericValue") or obs.get("Value")

            try:
                year = int(time) if time is not None else None
            except Exception:
                year = None

            try:
                val = float(numeric) if numeric is not None else None
            except Exception:
                val = None

            rows.append(
                GHORecord(
                    indicator=indicator,
                    spatial=str(spatial).upper() if spatial else None,
                    time=year,
                    value=val,
                    raw=obs,
                )
            )

        next_link = data.get("@odata.nextLink") or data.get("odata.nextLink")
        if isinstance(next_link, str) and next_link:
            next_url = next_link
            next_params = None  # nextLink already includes query params
        else:
            next_url = None

    df = pd.DataFrame([{"indicator": r.indicator, "iso3": r.spatial, "year": r.time, "value": r.value, **r.raw} for r in rows])
    if df.empty:
        return df
    return df.sort_values(["indicator", "iso3", "year"], na_position="last").reset_index(drop=True)

