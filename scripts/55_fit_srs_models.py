from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.model.gm import gm_hazard
from war_hunger_aging.model.gmh import fit_gompertz_makeham_hump, gmh_hazard


def _savefig(fig: plt.Figure, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def _fit_one(
    df: pd.DataFrame,
    *,
    adult_age_min: float,
    adult_age_max: float,
    fit_age_min: float,
    fit_age_max: float,
    mu_h: float,
    sigma_h: float,
    min_points: int,
) -> tuple[dict[str, object], dict[str, object]]:
    gm, gmh = fit_gompertz_makeham_hump(
        df,
        age_col="age",
        mx_col="mx",
        adult_age_min=adult_age_min,
        adult_age_max=adult_age_max,
        fit_age_min=fit_age_min,
        fit_age_max=fit_age_max,
        mu_h=mu_h,
        sigma_h=sigma_h,
        min_points=min_points,
    )

    gm_row = {
        "model": "gm",
        "a": gm.a,
        "b": gm.b,
        "c": gm.c,
        "h": np.nan,
        "converged": gm.converged,
        "rmse_log": gm.rmse_log,
        "rmse_log_adult": np.nan,
        "n": gm.n,
        "mrdt": gm.mrdt,
        "message": gm.message,
    }
    gmh_row = {
        "model": "gmh",
        "a": gmh.a,
        "b": gmh.b,
        "c": gmh.c,
        "h": gmh.h,
        "converged": gmh.converged,
        "rmse_log": gmh.rmse_log,
        "rmse_log_adult": gmh.rmse_log_adult,
        "n": gmh.n,
        "mrdt": gmh.mrdt,
        "message": gmh.message,
    }
    return gm_row, gmh_row


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit GM/GMH models to SRS abridged life tables (India + states).")
    ap.add_argument(
        "--in",
        dest="in_path",
        default="data/intermediate/srs_abridged_life_tables_2018_22.csv",
        help="Input CSV from scripts/05_extract_srs_life_tables.py",
    )
    ap.add_argument(
        "--adult-age-min",
        type=float,
        default=35.0,
        help="Minimum age (midpoint) for adult Gompertz-Makeham fit.",
    )
    ap.add_argument(
        "--fit-age-min",
        type=float,
        default=15.0,
        help="Minimum age (midpoint) for full GMH fit.",
    )
    ap.add_argument(
        "--min-points",
        type=int,
        default=12,
        help="Minimum number of age points required to attempt GMH fit (abridged tables have fewer ages).",
    )
    ap.add_argument(
        "--model",
        choices=["gm", "gmh", "both"],
        default="both",
        help="Which model results to keep for deltas/plots.",
    )
    ap.add_argument(
        "--overlay",
        action="store_true",
        help="Also write hazard overlay plots per area/sex (slower).",
    )
    args = ap.parse_args()

    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    in_path = Path(args.in_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Missing SRS CSV at {in_path.resolve()} (run scripts/05_extract_srs_life_tables.py).")

    df = pd.read_csv(in_path)
    df["mx"] = pd.to_numeric(df["mx"], errors="coerce")
    df["age_mid"] = pd.to_numeric(df["age_mid"], errors="coerce")
    df = df.dropna(subset=["age_mid"])

    # Keep closed intervals only for fitting (85+ has missing nqx/mx in the PDF).
    df_fit = df.dropna(subset=["mx"]).copy()
    if df_fit.empty:
        raise RuntimeError("No mx values found; check extraction output.")

    max_age_mid = float(df_fit["age_mid"].max())
    adult_age_max = max_age_mid
    fit_age_max = max_age_mid

    mu_h = float(cfg.hump.mu)
    sigma_h = float(cfg.hump.sigma)

    # Long-form to per-group fitting dataset.
    rows: list[dict[str, object]] = []
    group_cols = ["area", "period", "residence", "sex"]
    for (area, period, residence, sex), g in df_fit.groupby(group_cols):
        g2 = g[["age_mid", "mx"]].dropna().rename(columns={"age_mid": "age"}).copy()
        g2 = g2.sort_values("age")
        gm_row, gmh_row = _fit_one(
            g2,
            adult_age_min=float(args.adult_age_min),
            adult_age_max=adult_age_max,
            fit_age_min=float(args.fit_age_min),
            fit_age_max=fit_age_max,
            mu_h=mu_h,
            sigma_h=sigma_h,
            min_points=int(args.min_points),
        )
        base = {"area": area, "period": period, "residence": residence, "sex": sex}
        rows.append({**base, **gm_row})
        rows.append({**base, **gmh_row})

    params = pd.DataFrame(rows)
    out_params_parquet = cfg.paths.data_processed / "srs_params.parquet"
    out_params_csv = cfg.paths.reports_tables / "srs_params.csv"
    params.to_parquet(out_params_parquet, index=False)
    params.to_csv(out_params_csv, index=False)
    print(f"Wrote {out_params_parquet} ({len(params):,} rows)")
    print(f"Wrote {out_params_csv} ({len(params):,} rows)")

    keep_models = ["gm", "gmh"] if args.model == "both" else [args.model]
    params_keep = params[params["model"].isin(keep_models)].copy()

    # Build Urban–Rural deltas per area/sex/model for b and c.
    pivot = (
        params_keep.pivot_table(
            index=["area", "period", "sex", "model"],
            columns="residence",
            values=["b", "c", "h", "mrdt", "rmse_log"],
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    def col(metric: str, residence: str) -> str:
        return f"{metric}_{residence}"

    # Flatten multi-index columns produced by pivot_table.
    flat_cols = []
    for c in pivot.columns:
        if isinstance(c, tuple):
            if len(c) == 2:
                metric, residence = c
                if residence:
                    flat_cols.append(col(str(metric), str(residence)))
                else:
                    flat_cols.append(str(metric))
            else:
                flat_cols.append("_".join(str(x) for x in c if x))
        else:
            flat_cols.append(str(c))
    pivot.columns = flat_cols

    for metric in ["b", "c", "h", "mrdt", "rmse_log"]:
        if col(metric, "Urban") in pivot.columns and col(metric, "Rural") in pivot.columns:
            pivot[f"delta_{metric}_urban_minus_rural"] = pivot[col(metric, "Urban")] - pivot[col(metric, "Rural")]
            pivot[f"delta_{metric}_urban_minus_rural_pct"] = np.where(
                pivot[col(metric, "Rural")].astype(float) != 0,
                pivot[f"delta_{metric}_urban_minus_rural"] / pivot[col(metric, "Rural")].astype(float),
                np.nan,
            )

    out_deltas_parquet = cfg.paths.data_processed / "srs_urban_rural_deltas.parquet"
    out_deltas_csv = cfg.paths.reports_tables / "srs_urban_rural_deltas.csv"
    pivot.to_parquet(out_deltas_parquet, index=False)
    pivot.to_csv(out_deltas_csv, index=False)
    print(f"Wrote {out_deltas_parquet} ({len(pivot):,} rows)")
    print(f"Wrote {out_deltas_csv} ({len(pivot):,} rows)")

    # Plots: deltas by sex/model.
    sns.set_style("whitegrid")
    fig_dir = cfg.paths.reports_figures / "srs"

    for model in keep_models:
        for sex in sorted(params_keep["sex"].unique()):
            sub = pivot[(pivot["model"] == model) & (pivot["sex"] == sex)].copy()
            if sub.empty:
                continue

            # Scatter: delta_c vs delta_b.
            if {"delta_c_urban_minus_rural", "delta_b_urban_minus_rural"} <= set(sub.columns):
                fig, ax = plt.subplots(figsize=(7, 5))
                ax.axhline(0.0, color="0.6", lw=1)
                ax.axvline(0.0, color="0.6", lw=1)
                ax.scatter(
                    sub["delta_c_urban_minus_rural"],
                    sub["delta_b_urban_minus_rural"],
                    s=35,
                    alpha=0.9,
                )
                ax.set_title(f"SRS {model}: Urban − Rural (Δc vs Δb) — {sex}")
                ax.set_xlabel("Δc (Urban − Rural)")
                ax.set_ylabel("Δb (Urban − Rural)")
                _savefig(fig, fig_dir / f"delta_cb_urban_minus_rural_{model}_{sex}.png")

            # Bars for Δb and Δc.
            for metric in ["b", "c"]:
                dcol = f"delta_{metric}_urban_minus_rural"
                if dcol not in sub.columns:
                    continue
                srt = sub.sort_values(dcol, ascending=False)
                fig, ax = plt.subplots(figsize=(9, 6))
                ax.barh(srt["area"], srt[dcol], color="tab:blue", alpha=0.9)
                ax.axvline(0.0, color="0.6", lw=1)
                ax.set_title(f"SRS {model}: Urban − Rural (Δ{metric}) — {sex}")
                ax.set_xlabel(f"Δ{metric} (Urban − Rural)")
                ax.set_ylabel("Area")
                _savefig(fig, fig_dir / f"delta_{metric}_urban_minus_rural_{model}_{sex}.png")

    # Optional: hazard overlays per area/sex (adult range only).
    if args.overlay:
        obs = df_fit.copy()
        obs["age"] = obs["age_mid"].astype(float)
        obs["mx"] = obs["mx"].astype(float)
        obs = obs[obs["age"] >= float(args.fit_age_min)].copy()

        gm_params = params[params["model"] == "gm"].copy()
        gmh_params = params[params["model"] == "gmh"].copy()

        for sex in sorted(obs["sex"].unique()):
            for area in sorted(obs["area"].unique()):
                o = obs[(obs["sex"] == sex) & (obs["area"] == area)]
                if o.empty:
                    continue

                fig, ax = plt.subplots(figsize=(8, 5))
                for residence, color in [("Rural", "tab:green"), ("Urban", "tab:purple"), ("Total", "tab:gray")]:
                    oo = o[o["residence"] == residence].sort_values("age")
                    if oo.empty:
                        continue
                    ax.scatter(oo["age"], oo["mx"], s=25, alpha=0.85, color=color, label=f"obs {residence}")

                    p = gm_params[
                        (gm_params["sex"] == sex)
                        & (gm_params["area"] == area)
                        & (gm_params["residence"] == residence)
                    ]
                    if not p.empty and bool(p["converged"].iloc[0]):
                        a = float(p["a"].iloc[0])
                        b = float(p["b"].iloc[0])
                        c = float(p["c"].iloc[0])
                        ages = np.linspace(float(args.adult_age_min), max_age_mid, 120)
                        ax.plot(ages, gm_hazard(ages, a=a, b=b, c=c), color=color, lw=2, alpha=0.9)

                    if args.model in ("gmh", "both"):
                        p2 = gmh_params[
                            (gmh_params["sex"] == sex)
                            & (gmh_params["area"] == area)
                            & (gmh_params["residence"] == residence)
                        ]
                        if not p2.empty and bool(p2["converged"].iloc[0]):
                            a2 = float(p2["a"].iloc[0])
                            b2 = float(p2["b"].iloc[0])
                            c2 = float(p2["c"].iloc[0])
                            h2 = float(p2["h"].iloc[0])
                            ages = np.linspace(float(args.fit_age_min), max_age_mid, 160)
                            ax.plot(
                                ages,
                                gmh_hazard(ages, a=a2, b=b2, c=c2, h=h2, mu=mu_h, sigma=sigma_h),
                                color=color,
                                lw=1.5,
                                ls="--",
                                alpha=0.8,
                            )

                ax.set_yscale("log")
                ax.set_title(f"SRS hazard overlays — {area} — {sex}")
                ax.set_xlabel("Age (midpoint)")
                ax.set_ylabel("mx (from nqx)")
                ax.legend(ncol=2, fontsize=9)
                _savefig(fig, fig_dir / "overlays" / f"overlay_{area}_{sex}.png")


if __name__ == "__main__":
    main()

