from __future__ import annotations

from pathlib import Path

from war_hunger_aging.config import ensure_dirs, load_config
from war_hunger_aging.io.srs_life_tables import load_srs_abridged_life_tables_pdf, write_rows_csv


def main() -> None:
    cfg = load_config(Path("config/project.yml"))
    ensure_dirs(cfg)

    pdf = Path("SRS-Abridged_Life_Tables_2018-2022.pdf")
    if not pdf.exists():
        raise FileNotFoundError(f"Missing PDF at {pdf.resolve()}")

    rows = load_srs_abridged_life_tables_pdf(pdf)
    out_csv = cfg.paths.data_intermediate / "srs_abridged_life_tables_2018_22.csv"
    write_rows_csv(rows, out_csv)

    areas = sorted({str(r["area"]) for r in rows})
    residences = sorted({str(r["residence"]) for r in rows})
    sexes = sorted({str(r["sex"]) for r in rows})
    print(f"Wrote {out_csv} ({len(rows):,} rows)")
    print(f"Areas: {len(areas)}; Residences: {residences}; Sexes: {sexes}")

    # Optional parquet output when pandas/pyarrow are available.
    try:
        import pandas as pd  # type: ignore

        df = pd.DataFrame(rows)
        out_parquet = cfg.paths.data_intermediate / "srs_abridged_life_tables_2018_22.parquet"
        df.to_parquet(out_parquet, index=False)
        print(f"Wrote {out_parquet} ({len(df):,} rows)")
    except ModuleNotFoundError:
        pass


if __name__ == "__main__":
    main()

