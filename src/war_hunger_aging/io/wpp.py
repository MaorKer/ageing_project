from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_wpp_mx(path: str | Path) -> pd.DataFrame:
    """
    Load WPP age-specific death rates exported to parquet.

    Expected columns (minimum):
    - iso3 (ISO3)
    - year (int)
    - sex (Female/Male/Both)
    - mx (float)

    Age can be either:
    - age (single-age int/float), OR
    - age_start, age_end (bin bounds) -> we compute age as midpoint.
    """
    path = Path(path)
    if path.suffix.lower() in {".csv"}:
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".gz"} and path.name.lower().endswith(".csv.gz"):
        df = pd.read_csv(path, compression="gzip")
    else:
        df = pd.read_parquet(path)
    required = {"iso3", "year", "sex", "mx"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"WPP file missing columns {sorted(missing)} at {path}")

    out = df.copy()
    out["iso3"] = out["iso3"].astype(str).str.upper()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"])
    out["year"] = out["year"].astype(int)
    out["sex"] = out["sex"].astype(str)
    out["mx"] = pd.to_numeric(out["mx"], errors="coerce")

    if "age" in out.columns:
        out["age"] = pd.to_numeric(out["age"], errors="coerce")
    elif {"age_start", "age_end"} <= set(out.columns):
        out["age"] = (pd.to_numeric(out["age_start"], errors="coerce") + pd.to_numeric(out["age_end"], errors="coerce")) / 2.0
    else:
        raise KeyError("WPP parquet must include either 'age' or ('age_start','age_end').")

    out = out.dropna(subset=["age", "mx"])
    out = out.sort_values(["iso3", "year", "sex", "age"]).reset_index(drop=True)
    return out[["iso3", "year", "sex", "age", "mx"]]
