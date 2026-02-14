from __future__ import annotations

from pathlib import Path

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.wdi import fetch_indicators


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    inds = [
        cfg.wdi.indicators.population,
        cfg.wdi.indicators.pou,
        cfg.wdi.indicators.fies,
    ]
    df = fetch_indicators(inds, countries=cfg.countries, start_year=cfg.start_year, end_year=cfg.end_year)
    out = cfg.paths.data_intermediate / "wdi.parquet"
    df.to_parquet(out, index=False)
    print(f"Wrote {out} ({len(df):,} rows)")


if __name__ == "__main__":
    main()

