from __future__ import annotations

from pathlib import Path

import math
import pandas as pd
import typer
from rich import print

from war_hunger_aging.analysis.event_study import summarize_event_windows
from war_hunger_aging.analysis.regressions import run_fe_regression
from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io import ucdp as ucdp_io
from war_hunger_aging.io import wdi as wdi_io
from war_hunger_aging.io.wpp import load_wpp_mx
from war_hunger_aging.model.gmh import fit_gompertz_makeham_hump
from war_hunger_aging.model.gm import fit_gompertz_makeham
from war_hunger_aging.pipeline.build_panel import build_panels
from war_hunger_aging.viz.figures import (
    plot_hazard_overlays_pre_crisis_post,
    plot_param_timeseries_case_vs_controls,
    plot_war_hump_component,
)


app = typer.Typer(add_completion=False, help="War & hunger vs aging curves pipeline.")


@app.command()
def fetch_wdi(config: Path = typer.Option(Path("config/project.yml"), exists=True), force: bool = False) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)
    out = cfg.paths.data_intermediate / "wdi.parquet"
    if out.exists() and not force:
        print(f"[yellow]Skip[/yellow] WDI fetch; exists: {out}")
        return
    inds = [
        cfg.wdi.indicators.population,
        cfg.wdi.indicators.pou,
        cfg.wdi.indicators.fies,
    ]
    df = wdi_io.fetch_indicators(inds, countries=cfg.countries, start_year=cfg.start_year, end_year=cfg.end_year)
    df.to_parquet(out, index=False)
    print(f"[green]Wrote[/green] {out} ({len(df):,} rows)")


@app.command()
def prepare_ucdp(
    config: Path = typer.Option(Path("config/project.yml"), exists=True),
    input_path: Path | None = None,
    year_col: str | None = None,
    country_col: str | None = None,
    deaths_col: str | None = None,
    force: bool = False,
) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)
    out = cfg.paths.data_intermediate / "ucdp_brd.parquet"
    if out.exists() and not force:
        print(f"[yellow]Skip[/yellow] UCDP standardize; exists: {out}")
        return

    raw_dir = cfg.paths.data_raw / "ucdp"
    path = input_path or ucdp_io.discover_ucdp_file(raw_dir)
    std, unmapped, cols = ucdp_io.load_and_standardize_ucdp_brd(
        path=path,
        start_year=cfg.start_year,
        end_year=cfg.end_year,
        year_col=year_col,
        country_col=country_col,
        deaths_col=deaths_col,
    )
    std.to_parquet(out, index=False)
    if not unmapped.empty:
        unmapped_path = cfg.paths.data_intermediate / "ucdp_unmapped.parquet"
        unmapped.to_parquet(unmapped_path, index=False)
        print(f"[yellow]Unmapped countries[/yellow] saved to {unmapped_path}")
    print(f"[green]Wrote[/green] {out} ({len(std):,} rows). Inferred cols: {cols}")


@app.command()
def build_panel(config: Path = typer.Option(Path("config/project.yml"), exists=True), force: bool = False) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)

    wpp_path = cfg.paths.data_raw / "wpp_mx.parquet"
    if not wpp_path.exists():
        csv_fallback = cfg.paths.data_raw / "wpp_mx.csv"
        if csv_fallback.exists():
            wpp_path = csv_fallback
        else:
            raise FileNotFoundError(f"Missing WPP export: {wpp_path} (or {csv_fallback}). Run scripts/30_export_wpp_from_r.R")

    wdi_path = cfg.paths.data_intermediate / "wdi.parquet"
    ucdp_path = cfg.paths.data_intermediate / "ucdp_brd.parquet"
    if not wdi_path.exists():
        raise FileNotFoundError(f"Missing WDI file: {wdi_path}. Run scripts/10_fetch_wdi.py")
    if not ucdp_path.exists():
        raise FileNotFoundError(f"Missing UCDP file: {ucdp_path}. Run scripts/20_prepare_ucdp.py")

    out_dir = cfg.paths.data_processed
    panel_base = out_dir / "panel_base.parquet"
    panel_event = out_dir / "panel.parquet"
    groups_path = out_dir / "groups.parquet"
    if all(p.exists() for p in [panel_base, panel_event, groups_path]) and not force:
        print(f"[yellow]Skip[/yellow] build panel; outputs exist in {out_dir}")
        return

    mortality = load_wpp_mx(wpp_path)
    wdi_long = pd.read_parquet(wdi_path)
    ucdp = pd.read_parquet(ucdp_path)

    paths = build_panels(cfg=cfg, mortality=mortality, wdi_long=wdi_long, ucdp=ucdp, out_dir=out_dir)
    print(f"[green]Wrote[/green] {paths.panel_base}")
    print(f"[green]Wrote[/green] {paths.groups}")
    print(f"[green]Wrote[/green] {paths.panel_event}")


@app.command()
def fit_models(config: Path = typer.Option(Path("config/project.yml"), exists=True), force: bool = False) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)
    base_path = cfg.paths.data_processed / "panel_base.parquet"
    if not base_path.exists():
        raise FileNotFoundError(f"Missing panel: {base_path}. Run scripts/40_build_panel.py")

    out_params = cfg.paths.data_processed / "params.parquet"
    out_qc = cfg.paths.data_processed / "fit_qc.parquet"
    if out_params.exists() and out_qc.exists() and not force:
        print(f"[yellow]Skip[/yellow] fit models; outputs exist in {cfg.paths.data_processed}")
        return

    panel = pd.read_parquet(base_path)
    panel = panel[panel["sex"].isin(cfg.sexes)].copy()

    rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, object]] = []
    keys = ["iso3", "year", "sex"]
    for (iso3, year, sex), df in panel.groupby(keys):
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
        row = {
            "iso3": iso3,
            "year": int(year),
            "sex": sex,
            "a": a,
            "b": b,
            "c": c,
            "h": h,
            "mrdt": float(math.log(2.0) / float(b)) if (pd.notna(b) and float(b) > 0) else float("nan"),
            "converged": converged,
            "rmse_log_total": rmse_total,
            "rmse_log_adult": rmse_adult,
            "n_ages_total": n_total,
            "n_ages_adult": int(gm.n),
        }
        rows.append(row)
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

    params = pd.DataFrame(rows).sort_values(keys).reset_index(drop=True)
    qc = pd.DataFrame(qc_rows).sort_values(keys).reset_index(drop=True)
    params.to_parquet(out_params, index=False)
    qc.to_parquet(out_qc, index=False)
    print(f"[green]Wrote[/green] {out_params} ({len(params):,} rows)")
    print(f"[green]Wrote[/green] {out_qc} ({len(qc):,} rows)")


@app.command()
def make_figures(config: Path = typer.Option(Path("config/project.yml"), exists=True)) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)

    params_path = cfg.paths.data_processed / "params.parquet"
    base_path = cfg.paths.data_processed / "panel_base.parquet"
    if not params_path.exists() or not base_path.exists():
        raise FileNotFoundError("Missing params or panel_base. Run fit-models and build-panel first.")

    params = pd.read_parquet(params_path)
    base = pd.read_parquet(base_path)

    for group in cfg.cases:
        group_dict = {"id": group.id, "iso3": group.iso3, "t0": group.t0, "t1": group.t1, "controls": list(group.controls)}
        for sex in cfg.sexes:
            for param in ["b", "c", "h"]:
                out = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_timeseries_{param}.png"
                plot_param_timeseries_case_vs_controls(params=params, group=group_dict, param=param, sex=sex, outpath=out)
            out_hazard = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_hazard_overlays.png"
            plot_hazard_overlays_pre_crisis_post(panel_base=base, params=params, group=group_dict, sex=sex, outpath=out_hazard)
            out_hump = cfg.paths.reports_figures / f"{group.id}_{group.iso3}_{sex}_hump_component.png"
            plot_war_hump_component(params=params, group=group_dict, sex=sex, outpath=out_hump, period="crisis")

    print(f"[green]Wrote figures to[/green] {cfg.paths.reports_figures}")


@app.command()
def run_regressions(config: Path = typer.Option(Path("config/project.yml"), exists=True)) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)

    params_path = cfg.paths.data_processed / "params.parquet"
    base_path = cfg.paths.data_processed / "panel_base.parquet"
    if not params_path.exists() or not base_path.exists():
        raise FileNotFoundError("Missing params or panel_base. Run fit-models and build-panel first.")

    params = pd.read_parquet(params_path)
    base = pd.read_parquet(base_path)
    cov = base.groupby(["iso3", "year"], as_index=False)[
        ["battle_deaths_per_100k", "pou", "fies"]
    ].first()
    df = params.merge(cov, on=["iso3", "year"], how="left")

    for sex in cfg.sexes:
        sdf = df[df["sex"] == sex].copy()
        for outcome in ["c", "b", "h"]:
            if outcome not in sdf.columns:
                continue
            if sdf[outcome].dropna().empty:
                continue
            res = run_fe_regression(
                sdf,
                outcome=outcome,
                covariates=["battle_deaths_per_100k", "pou", "fies"],
            )
            txt_path = cfg.paths.reports_tables / f"regression_{outcome}_{sex}.txt"
            csv_path = cfg.paths.reports_tables / f"regression_{outcome}_{sex}_coef.csv"
            txt_path.write_text(str(res.result.summary()))
            coefs = res.result.params.to_frame("coef")
            coefs.to_csv(csv_path)
    print(f"[green]Wrote regression outputs to[/green] {cfg.paths.reports_tables}")


@app.command()
def build_report(config: Path = typer.Option(Path("config/project.yml"), exists=True)) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)
    methods_path = Path("reports/methods.md")
    results_path = Path("reports/results.md")
    report_path = Path("reports/report.md")

    methods = methods_path.read_text() if methods_path.exists() else "# Methods\n\n"
    results = results_path.read_text() if results_path.exists() else "# Results\n\n"

    figs = sorted(cfg.paths.reports_figures.glob("*.png"))
    tabs = [p for p in sorted(cfg.paths.reports_tables.glob("*.*")) if p.name != ".gitkeep"]

    lines: list[str] = []
    lines.append("# War & hunger vs aging curves — Report\n")
    lines.append(methods.strip() + "\n")
    lines.append(results.strip() + "\n")
    lines.append("## Figures\n")
    for p in figs:
        lines.append(f"- {p.as_posix()}")
    lines.append("\n## Tables\n")
    for p in tabs:
        lines.append(f"- {p.as_posix()}")
    report_path.write_text("\n".join(lines) + "\n")
    print(f"[green]Wrote[/green] {report_path}")


@app.command()
def event_summary(config: Path = typer.Option(Path("config/project.yml"), exists=True)) -> None:
    cfg = load_config(config)
    ensure_dirs(cfg)
    params_path = cfg.paths.data_processed / "params.parquet"
    groups_path = cfg.paths.data_processed / "groups.parquet"
    if not params_path.exists() or not groups_path.exists():
        raise FileNotFoundError("Missing params or groups. Run build-panel and fit-models first.")
    params = pd.read_parquet(params_path)
    groups = pd.read_parquet(groups_path)
    summary = summarize_event_windows(params=params, groups=groups, param_cols=["b", "c", "h", "mrdt"])
    out = cfg.paths.reports_tables / "event_summary.csv"
    summary.to_csv(out, index=False)
    print(f"[green]Wrote[/green] {out}")


if __name__ == "__main__":
    app()
