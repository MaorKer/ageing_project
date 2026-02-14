from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from war_hunger_aging.iso import iso3_from_name


@dataclass(frozen=True)
class UCDPColumns:
    year: str
    country: str
    deaths: str


def discover_ucdp_file(raw_dir: Path) -> Path:
    if not raw_dir.exists():
        raise FileNotFoundError(f"UCDP raw_dir not found: {raw_dir}")
    candidates: list[Path] = []
    for ext in ("*.csv", "*.tsv", "*.xlsx", "*.xls"):
        candidates.extend(sorted(raw_dir.glob(ext)))
    if not candidates:
        raise FileNotFoundError(
            f"No UCDP files found in {raw_dir}. Put the BRD download (CSV/XLSX) there."
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_any(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".csv"}:
        return pd.read_csv(path)
    if suffix in {".tsv"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported UCDP file type: {path.suffix}")


def infer_ucdp_columns(
    df: pd.DataFrame,
    *,
    year_candidates: Iterable[str] = ("year", "Year"),
    country_candidates: Iterable[str] = (
        "location",
        "Location",
        "country",
        "Country",
        "location_inc",
        "battle_location",
    ),
    deaths_candidates: Iterable[str] = (
        "bd_best",
        "best",
        "battle_deaths",
        "deaths",
        "deaths_best",
    ),
) -> UCDPColumns:
    cols = {c: c for c in df.columns}
    year_col = next((c for c in year_candidates if c in cols), None)
    country_col = next((c for c in country_candidates if c in cols), None)
    deaths_col = next((c for c in deaths_candidates if c in cols), None)
    missing = [k for k, v in [("year", year_col), ("country", country_col), ("deaths", deaths_col)] if v is None]
    if missing:
        raise KeyError(
            "Could not infer required UCDP columns: "
            + ", ".join(missing)
            + f". Available columns: {list(df.columns)}"
        )
    return UCDPColumns(year=year_col, country=country_col, deaths=deaths_col)


def standardize_ucdp_brd(
    df_raw: pd.DataFrame,
    *,
    cols: UCDPColumns,
    start_year: int,
    end_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (standardized, unmapped):
    - standardized: iso3, year, battle_deaths
    - unmapped: rows that failed country->iso3 mapping
    """
    df = df_raw[[cols.year, cols.country, cols.deaths]].copy()
    df = df.rename(columns={cols.year: "year", cols.country: "country", cols.deaths: "battle_deaths"})
    df = df.dropna(subset=["year", "country"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year"])
    df = df[(df["year"] >= start_year) & (df["year"] <= end_year)]
    df["battle_deaths"] = pd.to_numeric(df["battle_deaths"], errors="coerce").fillna(0.0)

    def _map_country(x: object) -> Optional[str]:
        if x is None:
            return None
        s = str(x).strip()
        if not s:
            return None
        return iso3_from_name(s)

    df["iso3"] = df["country"].map(_map_country)
    unmapped = df[df["iso3"].isna()].copy()
    mapped = df.dropna(subset=["iso3"]).copy()

    out = (
        mapped.groupby(["iso3", "year"], as_index=False)["battle_deaths"]
        .sum()
        .sort_values(["iso3", "year"])
        .reset_index(drop=True)
    )
    out["year"] = out["year"].astype(int)
    out["battle_deaths"] = out["battle_deaths"].astype(float)
    return out, unmapped


def load_and_standardize_ucdp_brd(
    *,
    path: Path,
    start_year: int,
    end_year: int,
    year_col: str | None = None,
    country_col: str | None = None,
    deaths_col: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, UCDPColumns]:
    df_raw = _read_any(path)
    if year_col and country_col and deaths_col:
        cols = UCDPColumns(year=year_col, country=country_col, deaths=deaths_col)
    else:
        cols = infer_ucdp_columns(df_raw)
    std, unmapped = standardize_ucdp_brd(df_raw, cols=cols, start_year=start_year, end_year=end_year)
    return std, unmapped, cols
