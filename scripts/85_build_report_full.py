from __future__ import annotations

import datetime as dt
from pathlib import Path

from war_hunger_aging.config import load_config


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _code_block(text: str, *, lang: str = "") -> str:
    text = text.rstrip("\n")
    fence = "```"
    return f"{fence}{lang}\n{text}\n{fence}\n"


def _md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for r in rows:
        vals = []
        for c in columns:
            v = r.get(c, "")
            if v is None:
                vals.append("")
            elif isinstance(v, float):
                vals.append(f"{v:.4g}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    cfg = load_config(Path("config/project.yml"))

    reports_dir = Path("reports")
    figures_dir = reports_dir / "figures"
    tables_dir = reports_dir / "tables"
    reports_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    methods_md = _read_text(reports_dir / "methods.md").strip()
    results_md = _read_text(reports_dir / "results.md").strip()

    params_path = Path("data/processed/params.parquet")
    groups_path = Path("data/processed/groups.parquet")
    panel_base_path = Path("data/processed/panel_base.parquet")

    try:
        import pandas as pd  # type: ignore
    except ModuleNotFoundError:
        pd = None  # type: ignore[assignment]

    now = dt.datetime.now().astimezone()

    lines: list[str] = []
    lines.append("# War, hunger, and aging curves — Full Results\n")
    lines.append(f"_Generated: {now:%Y-%m-%d %H:%M %Z}_\n")

    if methods_md:
        lines.append(methods_md + "\n")

    lines.append("## Outputs\n")
    outputs = [
        ("Panel (base)", panel_base_path),
        ("Fitted params", params_path),
        ("Fit QC", Path("data/processed/fit_qc.parquet")),
        ("WDI extra series (optional)", Path("data/intermediate/wdi_extra.parquet")),
        ("WHO GHO series (optional)", Path("data/intermediate/who_gho.parquet")),
        ("SRS (India) extracted table", Path("data/intermediate/srs_abridged_life_tables_2018_22.csv")),
        ("SRS (India) fitted params", Path("data/processed/srs_params.parquet")),
        ("SRS (India) Urban–Rural deltas", Path("data/processed/srs_urban_rural_deltas.parquet")),
        ("SRS (India) figures", figures_dir / "srs"),
        ("Figures", figures_dir),
        ("Tables", tables_dir),
    ]
    for label, p in outputs:
        lines.append(f"- **{label}:** `{p.as_posix()}`")
    lines.append("")

    # Optional: India SRS add-on section (if the extracted CSV exists).
    srs_csv = Path("data/intermediate/srs_abridged_life_tables_2018_22.csv")
    srs_fig_dir = figures_dir / "srs"
    if srs_csv.exists():
        lines.append("## India (SRS) Add-on\n")
        lines.append("This repo can also fit GM/GMH on India’s SRS abridged life tables (2018–22) by `area × residence × sex`.\n")
        lines.append("Run:\n")
        lines.append(_code_block("python3 scripts/05_extract_srs_life_tables.py\npython3 scripts/55_fit_srs_models.py", lang="bash"))
        lines.append("Key outputs:\n")
        lines.append("- `data/intermediate/srs_abridged_life_tables_2018_22.csv` (tidy extraction + derived `mx`)\n")
        lines.append("- `data/processed/srs_params.parquet` and `reports/tables/srs_params.csv`\n")
        lines.append("- `data/processed/srs_urban_rural_deltas.parquet` and `reports/tables/srs_urban_rural_deltas.csv`\n")
        if srs_fig_dir.exists():
            lines.append(f"- Figures: `{srs_fig_dir.as_posix()}`\n")
        lines.append("")

        if srs_fig_dir.exists():
            lines.append("### SRS Figures\n")
            for p in sorted(srs_fig_dir.glob("*.png")):
                rel = p.relative_to(reports_dir)
                lines.append(f"![{p.stem}]({rel.as_posix()})\n")
            overlays = srs_fig_dir / "overlays"
            if overlays.exists():
                n_overlay = len(list(overlays.glob("*.png")))
                lines.append(f"- Overlays directory: `{overlays.as_posix()}` ({n_overlay} pngs)\n")

    # Basic summary stats (if present).
    if pd is not None and params_path.exists():
        params = pd.read_parquet(params_path)
        n_total = int(params.shape[0])
        n_conv = int(params["converged"].sum()) if "converged" in params.columns else 0
        lines.append("## Fit Summary\n")
        lines.append(f"- Fits: **{n_total:,}** (rows in `data/processed/params.parquet`)")
        lines.append(f"- Converged: **{n_conv:,}** ({(n_conv / max(n_total, 1)):.1%})")
        if {"iso3", "sex"} <= set(params.columns):
            by = (
                params.groupby(["iso3", "sex"], as_index=False)["converged"]
                .mean()
                .rename(columns={"converged": "converged_rate"})
                .sort_values(["iso3", "sex"])
            )
            sample = by.to_dict(orient="records")[:20]
            lines.append("\n### Convergence Rate (sample)\n")
            lines.append(_md_table(sample, ["iso3", "sex", "converged_rate"]))
    elif params_path.exists():
        lines.append("## Fit Summary\n")
        lines.append("- (Skipped: `pandas` not available in this environment.)\n")

    # Event summary (case countries only) + full CSV in appendix.
    if pd is not None and params_path.exists() and groups_path.exists():
        from war_hunger_aging.analysis.event_study import summarize_event_windows

        params = pd.read_parquet(params_path)
        groups = pd.read_parquet(groups_path)
        summary = summarize_event_windows(params=params, groups=groups, param_cols=["b", "c", "h", "mrdt"])
        summary = summary.merge(groups[["case_group", "iso3", "is_case_country"]], on=["case_group", "iso3"], how="left")
        out_csv = tables_dir / "event_summary.csv"
        summary.to_csv(out_csv, index=False)

        lines.append("## Event-Window Summary (Cases)\n")
        cases = summary[summary["is_case_country"] == True].copy()  # noqa: E712
        cases = cases.sort_values(["case_group", "sex", "param"])
        rows = []
        for _, r in cases.iterrows():
            rows.append(
                {
                    "case_group": r["case_group"],
                    "iso3": r["iso3"],
                    "sex": r["sex"],
                    "param": r["param"],
                    "crisis_minus_pre": r["crisis_minus_pre"],
                }
            )
        lines.append(_md_table(rows, ["case_group", "iso3", "sex", "param", "crisis_minus_pre"]))
        lines.append(f"Full CSV: `{out_csv.as_posix()}`\n")
    elif params_path.exists() and groups_path.exists():
        lines.append("## Event-Window Summary (Cases)\n")
        lines.append("- (Skipped: `pandas` not available in this environment.)\n")

    # Figures
    lines.append("## Figures\n")
    for group in cfg.cases:
        lines.append(f"### {group.id} — {group.iso3}\n")
        for sex in cfg.sexes:
            lines.append(f"#### {sex}\n")
            img_paths = [
                figures_dir / f"{group.id}_{group.iso3}_{sex}_timeseries_b.png",
                figures_dir / f"{group.id}_{group.iso3}_{sex}_timeseries_c.png",
                figures_dir / f"{group.id}_{group.iso3}_{sex}_timeseries_h.png",
                figures_dir / f"{group.id}_{group.iso3}_{sex}_hazard_overlays.png",
                figures_dir / f"{group.id}_{group.iso3}_{sex}_hump_component.png",
            ]
            for p in img_paths:
                if p.exists():
                    rel = p.relative_to(reports_dir)
                    lines.append(f"![{p.stem}]({rel.as_posix()})\n")
                else:
                    lines.append(f"- Missing: `{p.as_posix()}`\n")

    # Regression outputs
    lines.append("## Regressions\n")
    for sex in cfg.sexes:
        lines.append(f"### {sex}\n")
        for outcome in ["c", "b", "h"]:
            txt = tables_dir / f"regression_{outcome}_{sex}.txt"
            coef = tables_dir / f"regression_{outcome}_{sex}_coef.csv"
            if not txt.exists():
                continue
            lines.append(f"#### Outcome: `{outcome}`\n")
            lines.append(_code_block(_read_text(txt), lang="text"))
            if coef.exists():
                lines.append(f"Coefficients CSV: `{coef.as_posix()}`\n")

    if results_md:
        lines.append("\n## Notes\n")
        lines.append(results_md + "\n")

    out_md = reports_dir / "report_full.md"
    out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
