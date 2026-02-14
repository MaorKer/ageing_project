from __future__ import annotations

from pathlib import Path

import pandas as pd

from war_hunger_aging.analysis.regressions import run_fe_regression
from war_hunger_aging.config import ensure_dirs, load_config


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    params = pd.read_parquet(cfg.paths.data_processed / "params.parquet")
    base = pd.read_parquet(cfg.paths.data_processed / "panel_base.parquet")
    cov = base.groupby(["iso3", "year"], as_index=False)[
        ["battle_deaths_per_100k", "pou", "fies"]
    ].first()
    df = params.merge(cov, on=["iso3", "year"], how="left")

    for sex in cfg.sexes:
        sdf = df[df["sex"] == sex].copy()
        for outcome in ["c", "b", "h"]:
            if outcome not in sdf.columns or sdf[outcome].dropna().empty:
                continue
            res = run_fe_regression(
                sdf,
                outcome=outcome,
                covariates=["battle_deaths_per_100k", "pou", "fies"],
            )
            txt_path = cfg.paths.reports_tables / f"regression_{outcome}_{sex}.txt"
            csv_path = cfg.paths.reports_tables / f"regression_{outcome}_{sex}_coef.csv"
            txt_path.write_text(str(res.result.summary()))
            res.result.params.to_frame("coef").to_csv(csv_path)
            print(f"Wrote {txt_path} and {csv_path}")


if __name__ == "__main__":
    main()
