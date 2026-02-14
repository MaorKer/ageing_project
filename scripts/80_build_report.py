from __future__ import annotations

from pathlib import Path

from war_hunger_aging.config import ensure_dirs, load_config


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
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
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
