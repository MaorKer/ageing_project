from __future__ import annotations

import argparse
from pathlib import Path

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.wdi import fetch_indicators


DEFAULT_INDICATORS = [
    # Life expectancy at birth (years)
    "SP.DYN.LE00.IN",
    "SP.DYN.LE00.MA.IN",
    "SP.DYN.LE00.FE.IN",
    # Child mortality
    "SP.DYN.IMRT.IN",  # infant mortality rate (per 1,000 live births)
    "SH.DYN.MORT",  # under-5 mortality rate (per 1,000 live births)
    # Adult mortality (per 1,000 adults) – indicator codes exist in WDI but coverage varies.
    "SP.DYN.AMRT.MA",
    "SP.DYN.AMRT.FE",
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch additional WDI indicators (life expectancy + mortality).")
    ap.add_argument(
        "--ind",
        dest="inds",
        action="append",
        default=[],
        help="Indicator code to fetch (repeatable). If omitted, uses a default set.",
    )
    args = ap.parse_args()

    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    inds = args.inds or DEFAULT_INDICATORS
    df = fetch_indicators(inds, countries=cfg.countries, start_year=cfg.start_year, end_year=cfg.end_year)

    out_parquet = cfg.paths.data_intermediate / "wdi_extra.parquet"
    out_csv = cfg.paths.data_intermediate / "wdi_extra.csv"
    df.to_parquet(out_parquet, index=False)
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_parquet} ({len(df):,} rows)")
    print(f"Wrote {out_csv} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
