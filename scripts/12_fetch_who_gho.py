from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.who_gho import fetch_gho_indicator


DEFAULT_INDICATORS = [
    # Commonly used GHO code for life expectancy at birth (years).
    # If this changes or you want other series, pass --ind manually.
    "WHOSIS_000001",
]


def _country_filter(iso3s: list[str]) -> str:
    parts = [f"SpatialDim eq '{c}'" for c in iso3s]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return "(" + " or ".join(parts) + ")"


def _year_filter(start_year: int, end_year: int) -> str:
    return f"(TimeDim ge {start_year} and TimeDim le {end_year})"


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch WHO GHO indicator series via OData API.")
    ap.add_argument(
        "--ind",
        dest="inds",
        action="append",
        default=[],
        help="Indicator code to fetch (repeatable). Default: WHOSIS_000001 (life expectancy at birth).",
    )
    ap.add_argument(
        "--all-countries",
        action="store_true",
        help="Do not filter to config countries (can be very large).",
    )
    ap.add_argument("--start-year", type=int, default=None)
    ap.add_argument("--end-year", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    inds = args.inds or DEFAULT_INDICATORS
    start_year = int(args.start_year) if args.start_year is not None else int(cfg.start_year)
    end_year = int(args.end_year) if args.end_year is not None else int(cfg.end_year)

    where_parts = [_year_filter(start_year, end_year)]
    if not args.all_countries:
        where_parts.append(_country_filter(list(cfg.countries)))
    where = " and ".join([p for p in where_parts if p])

    frames: list[pd.DataFrame] = []
    for ind in inds:
        frames.append(fetch_gho_indicator(ind, where=where if where else None))

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out_parquet = cfg.paths.data_intermediate / "who_gho.parquet"
    out_csv = cfg.paths.data_intermediate / "who_gho.csv"
    df.to_parquet(out_parquet, index=False)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_parquet} ({len(df):,} rows)")
    print(f"Wrote {out_csv} ({len(df):,} rows)")


if __name__ == "__main__":
    main()

