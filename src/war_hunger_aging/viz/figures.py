from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from war_hunger_aging.model.gmh import hump, gmh_hazard


def _shade_crisis(ax: plt.Axes, *, t0: int, t1: int) -> None:
    ax.axvspan(t0, t1, color="0.9", zorder=0)


def plot_param_timeseries_case_vs_controls(
    *,
    params: pd.DataFrame,
    group: dict[str, object],
    param: str,
    sex: str,
    outpath: Path,
) -> None:
    """
    Plot case series and mean of controls for a single case_group and sex.
    """
    case_iso3 = str(group["iso3"])
    controls = list(group["controls"])
    t0 = int(group["t0"])
    t1 = int(group["t1"])
    group_id = str(group["id"])

    df = params[(params["sex"] == sex) & (params["iso3"].isin([case_iso3, *controls]))].copy()
    if df.empty:
        return

    case = df[df["iso3"] == case_iso3][["year", param]].dropna()
    ctrl = df[df["iso3"].isin(controls)][["iso3", "year", param]].dropna()
    ctrl_mean = ctrl.groupby("year")[param].mean().reset_index()

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(9, 4))
    _shade_crisis(ax, t0=t0, t1=t1)
    if not ctrl_mean.empty:
        ax.plot(ctrl_mean["year"], ctrl_mean[param], label="controls mean", color="tab:blue")
    if not case.empty:
        ax.plot(case["year"], case[param], label=f"case {case_iso3}", color="tab:red")
    ax.set_title(f"{group_id} — {param} — {sex}")
    ax.set_xlabel("Year")
    ax.set_ylabel(param)
    ax.legend()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_hazard_overlays_pre_crisis_post(
    *,
    panel_base: pd.DataFrame,
    params: pd.DataFrame,
    group: dict[str, object],
    sex: str,
    outpath: Path,
    logy: bool = True,
) -> None:
    """
    For the case country only: average observed hazard by age for pre/crisis/post
    and overlay model predictions using mean parameters in each period.
    """
    case_iso3 = str(group["iso3"])
    t0 = int(group["t0"])
    t1 = int(group["t1"])

    df = panel_base[(panel_base["iso3"] == case_iso3) & (panel_base["sex"] == sex)].copy()
    if df.empty:
        return

    def period_of_year(y: int) -> str:
        if t0 - 5 <= y <= t0 - 1:
            return "pre"
        if t0 <= y <= t1:
            return "crisis"
        if y >= t1 + 1:
            return "post"
        return "other"

    df["period"] = df["year"].map(period_of_year)
    df = df[df["period"].isin(["pre", "crisis", "post"])].copy()
    if df.empty:
        return

    obs = df.groupby(["period", "age"], as_index=False)["mx"].mean()

    p = params[(params["iso3"] == case_iso3) & (params["sex"] == sex)].copy()
    p["period"] = p["year"].map(period_of_year)
    p = p[p["period"].isin(["pre", "crisis", "post"])]

    period_params = p.groupby("period")[["a", "b", "c", "h"]].mean(numeric_only=True)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(7, 5))
    palette = {"pre": "tab:green", "crisis": "tab:orange", "post": "tab:purple"}

    for period, odf in obs.groupby("period"):
        ax.plot(odf["age"], odf["mx"], label=f"obs {period}", color=palette.get(period, "0.4"), lw=2)
        if period in period_params.index and {"a", "b", "c"} <= set(period_params.columns):
            a = float(period_params.loc[period, "a"])
            b = float(period_params.loc[period, "b"])
            c = float(period_params.loc[period, "c"])
            h_val = float(period_params.loc[period, "h"]) if "h" in period_params.columns else 0.0
            ages = odf["age"].to_numpy(dtype=float)
            pred = gmh_hazard(ages, a=a, b=b, c=c, h=h_val, mu=28, sigma=10)
            ax.plot(ages, pred, ls="--", color=palette.get(period, "0.4"), alpha=0.9, label=f"model {period}")

    ax.set_title(f"{group['id']} — {case_iso3} — hazard overlays — {sex}")
    ax.set_xlabel("Age")
    ax.set_ylabel("mx (hazard proxy)")
    if logy:
        ax.set_yscale("log")
    ax.legend(ncol=2, fontsize=9)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_war_hump_component(
    *,
    params: pd.DataFrame,
    group: dict[str, object],
    sex: str,
    outpath: Path,
    ages: np.ndarray | None = None,
    period: str = "crisis",
) -> None:
    """
    Plot the fitted hump component for the case country using mean h in the chosen period.
    """
    case_iso3 = str(group["iso3"])
    t0 = int(group["t0"])
    t1 = int(group["t1"])

    def period_of_year(y: int) -> str:
        if t0 - 5 <= y <= t0 - 1:
            return "pre"
        if t0 <= y <= t1:
            return "crisis"
        if y >= t1 + 1:
            return "post"
        return "other"

    df = params[(params["iso3"] == case_iso3) & (params["sex"] == sex)].copy()
    if df.empty or "h" not in df.columns:
        return
    df["period"] = df["year"].map(period_of_year)
    df = df[df["period"] == period]
    if df.empty:
        return

    h_mean = float(df["h"].mean())
    if ages is None:
        ages = np.arange(10, 60, dtype=float)
    comp = hump(ages, h=h_mean, mu=28, sigma=10)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ages, comp, color="tab:red")
    ax.set_title(f"{group['id']} — {case_iso3} — hump component ({period}) — {sex}")
    ax.set_xlabel("Age")
    ax.set_ylabel("hump hazard")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)

