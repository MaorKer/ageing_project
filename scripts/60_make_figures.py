from __future__ import annotations

from pathlib import Path

import pandas as pd

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.viz.figures import (
    plot_hazard_overlays_pre_crisis_post,
    plot_param_timeseries_case_vs_controls,
    plot_war_hump_component,
)


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    params = pd.read_parquet(cfg.paths.data_processed / "params.parquet")
    panel_base = pd.read_parquet(cfg.paths.data_processed / "panel_base.parquet")

    for group in cfg.cases:
        group_dict = {"id": group.id, "iso3": group.iso3, "t0": group.t0, "t1": group.t1, "controls": list(group.controls)}
        for sex in cfg.sexes:
            for param in ["b", "c", "h"]:
                out = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_timeseries_{param}.png"
                plot_param_timeseries_case_vs_controls(params=params, group=group_dict, param=param, sex=sex, outpath=out)
            out_hazard = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_hazard_overlays.png"
            plot_hazard_overlays_pre_crisis_post(panel_base=panel_base, params=params, group=group_dict, sex=sex, outpath=out_hazard)
            out_hump = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_hump_component.png"
            plot_war_hump_component(params=params, group=group_dict, sex=sex, outpath=out_hump, period="crisis")

    print(f"Wrote figures to {cfg.paths.reports_figures}")


if __name__ == "__main__":
    main()

