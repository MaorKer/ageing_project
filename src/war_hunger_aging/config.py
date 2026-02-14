from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AgeRange:
    min: int
    max: int


@dataclass(frozen=True)
class HumpSpec:
    enabled: bool
    mu: float
    sigma: float


@dataclass(frozen=True)
class CaseGroup:
    id: str
    iso3: str
    t0: int
    t1: int
    controls: tuple[str, ...]

    @property
    def all_countries(self) -> tuple[str, ...]:
        return (self.iso3, *self.controls)


@dataclass(frozen=True)
class WDIIndicators:
    population: str
    pou: str
    fies: str


@dataclass(frozen=True)
class WDIConfig:
    indicators: WDIIndicators
    interpolate: bool


@dataclass(frozen=True)
class Paths:
    data_raw: Path
    data_intermediate: Path
    data_processed: Path
    reports_figures: Path
    reports_tables: Path


@dataclass(frozen=True)
class ProjectConfig:
    start_year: int
    end_year: int
    sexes: tuple[str, ...]
    adult_ages: AgeRange
    hump_ages: AgeRange
    fit_ages: AgeRange
    hump: HumpSpec
    cases: tuple[CaseGroup, ...]
    wdi: WDIConfig
    paths: Paths

    @property
    def countries(self) -> tuple[str, ...]:
        unique: dict[str, None] = {}
        for group in self.cases:
            for code in group.all_countries:
                unique[code] = None
        return tuple(unique.keys())


DEFAULT_CONFIG_PATH = Path("config/project.yml")


def _require(d: dict[str, Any], key: str, *, ctx: str) -> Any:
    if key not in d:
        raise KeyError(f"Missing required key '{key}' in {ctx}.")
    return d[key]


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> ProjectConfig:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise TypeError(f"Config at {path} must be a mapping.")

    project = _require(raw, "project", ctx="root")
    cases_raw = _require(raw, "cases", ctx="root")
    wdi_raw = _require(raw, "wdi", ctx="root")
    paths_raw = _require(raw, "paths", ctx="root")

    start_year = int(_require(project, "start_year", ctx="project"))
    end_year = int(_require(project, "end_year", ctx="project"))
    if start_year > end_year:
        raise ValueError("project.start_year must be <= project.end_year.")

    sexes = tuple(_require(project, "sexes", ctx="project"))
    if not sexes:
        raise ValueError("project.sexes must be non-empty.")

    ages = _require(project, "ages", ctx="project")
    adult = AgeRange(**_require(ages, "adult", ctx="project.ages"))
    hump_ages = AgeRange(**_require(ages, "hump", ctx="project.ages"))
    fit_ages = AgeRange(**_require(ages, "fit", ctx="project.ages"))

    hump = HumpSpec(**_require(project, "hump", ctx="project"))

    cases: list[CaseGroup] = []
    if not isinstance(cases_raw, list) or not cases_raw:
        raise ValueError("cases must be a non-empty list.")
    for idx, entry in enumerate(cases_raw):
        if not isinstance(entry, dict):
            raise TypeError(f"cases[{idx}] must be a mapping.")
        controls = tuple(entry.get("controls", []))
        cases.append(
            CaseGroup(
                id=str(_require(entry, "id", ctx=f"cases[{idx}]")),
                iso3=str(_require(entry, "iso3", ctx=f"cases[{idx}]")).upper(),
                t0=int(_require(entry, "t0", ctx=f"cases[{idx}]")),
                t1=int(_require(entry, "t1", ctx=f"cases[{idx}]")),
                controls=tuple(str(x).upper() for x in controls),
            )
        )

    indicators_raw = _require(wdi_raw, "indicators", ctx="wdi")
    indicators = WDIIndicators(
        population=str(_require(indicators_raw, "population", ctx="wdi.indicators")),
        pou=str(_require(indicators_raw, "pou", ctx="wdi.indicators")),
        fies=str(_require(indicators_raw, "fies", ctx="wdi.indicators")),
    )
    wdi = WDIConfig(indicators=indicators, interpolate=bool(wdi_raw.get("interpolate", True)))

    paths = Paths(
        data_raw=Path(_require(paths_raw, "data_raw", ctx="paths")),
        data_intermediate=Path(_require(paths_raw, "data_intermediate", ctx="paths")),
        data_processed=Path(_require(paths_raw, "data_processed", ctx="paths")),
        reports_figures=Path(_require(paths_raw, "reports_figures", ctx="paths")),
        reports_tables=Path(_require(paths_raw, "reports_tables", ctx="paths")),
    )

    return ProjectConfig(
        start_year=start_year,
        end_year=end_year,
        sexes=sexes,
        adult_ages=adult,
        hump_ages=hump_ages,
        fit_ages=fit_ages,
        hump=hump,
        cases=tuple(cases),
        wdi=wdi,
        paths=paths,
    )


def ensure_dirs(cfg: ProjectConfig) -> None:
    cfg.paths.data_raw.mkdir(parents=True, exist_ok=True)
    cfg.paths.data_intermediate.mkdir(parents=True, exist_ok=True)
    cfg.paths.data_processed.mkdir(parents=True, exist_ok=True)
    cfg.paths.reports_figures.mkdir(parents=True, exist_ok=True)
    cfg.paths.reports_tables.mkdir(parents=True, exist_ok=True)

