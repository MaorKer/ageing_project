from __future__ import annotations

import argparse
from pathlib import Path

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.ucdp import discover_ucdp_file, load_and_standardize_ucdp_brd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standardize UCDP BRD to iso3-year battle_deaths parquet.")
    p.add_argument("--input", type=Path, default=None, help="Path to UCDP BRD file (CSV/XLSX). If omitted, auto-discovers in data/raw/ucdp/.")
    p.add_argument("--year-col", type=str, default=None)
    p.add_argument("--country-col", type=str, default=None)
    p.add_argument("--deaths-col", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    raw_dir = cfg.paths.data_raw / "ucdp"
    path = args.input or discover_ucdp_file(raw_dir)
    std, unmapped, cols = load_and_standardize_ucdp_brd(
        path=path,
        start_year=cfg.start_year,
        end_year=cfg.end_year,
        year_col=args.year_col,
        country_col=args.country_col,
        deaths_col=args.deaths_col,
    )
    out = cfg.paths.data_intermediate / "ucdp_brd.parquet"
    std.to_parquet(out, index=False)
    print(f"Wrote {out} ({len(std):,} rows). Inferred cols: {cols}")
    if not unmapped.empty:
        unmapped_out = cfg.paths.data_intermediate / "ucdp_unmapped.parquet"
        unmapped.to_parquet(unmapped_out, index=False)
        print(f"Unmapped rows saved to {unmapped_out} ({len(unmapped):,} rows)")


if __name__ == "__main__":
    main()

