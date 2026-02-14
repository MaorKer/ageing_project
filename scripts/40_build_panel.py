from __future__ import annotations

from pathlib import Path

import pandas as pd

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.wpp import load_wpp_mx
from war_hunger_aging.pipeline.build_panel import build_panels


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    wpp_path = cfg.paths.data_raw / "wpp_mx.parquet"
    if not wpp_path.exists():
        csv_fallback = cfg.paths.data_raw / "wpp_mx.csv"
        if csv_fallback.exists():
            wpp_path = csv_fallback
    wdi_path = cfg.paths.data_intermediate / "wdi.parquet"
    ucdp_path = cfg.paths.data_intermediate / "ucdp_brd.parquet"

    mortality = load_wpp_mx(wpp_path)
    wdi_long = pd.read_parquet(wdi_path)
    ucdp = pd.read_parquet(ucdp_path)

    paths = build_panels(cfg=cfg, mortality=mortality, wdi_long=wdi_long, ucdp=ucdp, out_dir=cfg.paths.data_processed)
    print(f"Wrote {paths.panel_base}")
    print(f"Wrote {paths.groups}")
    print(f"Wrote {paths.panel_event}")


if __name__ == "__main__":
    main()
