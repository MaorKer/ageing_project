from __future__ import annotations

from pathlib import Path

import pandas as pd

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.model.gmh import fit_gompertz_makeham_hump
from war_hunger_aging.model.gm import fit_gompertz_makeham


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    panel_path = cfg.paths.data_processed / "panel_base.parquet"
    panel = pd.read_parquet(panel_path)
    panel = panel[panel["sex"].isin(cfg.sexes)].copy()

    rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, object]] = []
    for (iso3, year, sex), df in panel.groupby(["iso3", "year", "sex"]):
        if cfg.hump.enabled:
            gm, gmh = fit_gompertz_makeham_hump(
                df,
                adult_age_min=cfg.adult_ages.min,
                adult_age_max=cfg.adult_ages.max,
                fit_age_min=cfg.fit_ages.min,
                fit_age_max=cfg.fit_ages.max,
                mu_h=cfg.hump.mu,
                sigma_h=cfg.hump.sigma,
            )
            a, b, c, h = gmh.a, gmh.b, gmh.c, gmh.h
            converged = bool(gmh.converged)
            rmse_total = float(gmh.rmse_log)
            rmse_adult = float(gmh.rmse_log_adult)
            n_total = int(gmh.n)
            message = gmh.message
        else:
            gm = fit_gompertz_makeham(
                df,
                age_min=cfg.adult_ages.min,
                age_max=cfg.adult_ages.max,
            )
            a, b, c, h = gm.a, gm.b, gm.c, float("nan")
            converged = bool(gm.converged)
            rmse_total = float(gm.rmse_log)
            rmse_adult = float(gm.rmse_log)
            n_total = int(gm.n)
            message = gm.message
        rows.append(
            {
                "iso3": iso3,
                "year": int(year),
                "sex": sex,
                "a": a,
                "b": b,
                "c": c,
                "h": h,
                "mrdt": gmh.mrdt if cfg.hump.enabled else gm.mrdt,
                "converged": converged,
                "rmse_log_total": rmse_total,
                "rmse_log_adult": rmse_adult,
                "n_ages_total": n_total,
                "n_ages_adult": int(gm.n),
            }
        )
        qc_rows.append(
            {
                "iso3": iso3,
                "year": int(year),
                "sex": sex,
                "gm_message": gm.message,
                "gm_converged": bool(gm.converged),
                "gm_rmse_log": float(gm.rmse_log),
                "gm_a": gm.a,
                "gm_b": gm.b,
                "gm_c": gm.c,
                "gmh_message": message,
                "gmh_converged": converged,
            }
        )

    params = pd.DataFrame(rows).sort_values(["iso3", "year", "sex"]).reset_index(drop=True)
    qc = pd.DataFrame(qc_rows).sort_values(["iso3", "year", "sex"]).reset_index(drop=True)

    out_params = cfg.paths.data_processed / "params.parquet"
    out_qc = cfg.paths.data_processed / "fit_qc.parquet"
    params.to_parquet(out_params, index=False)
    qc.to_parquet(out_qc, index=False)
    print(f"Wrote {out_params} ({len(params):,} rows)")
    print(f"Wrote {out_qc} ({len(qc):,} rows)")


if __name__ == "__main__":
    main()
