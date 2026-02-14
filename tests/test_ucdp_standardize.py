from __future__ import annotations

import pandas as pd

from war_hunger_aging.io.ucdp import infer_ucdp_columns, standardize_ucdp_brd


def test_ucdp_standardization_maps_iso3_and_sums() -> None:
    raw = pd.DataFrame(
        {
            "year": [2015, 2015, 2016],
            "location": ["Yemen", "Yemen", "Syrian Arab Republic"],
            "bd_best": [10, 5, 7],
        }
    )
    cols = infer_ucdp_columns(raw)
    std, unmapped = standardize_ucdp_brd(raw, cols=cols, start_year=2010, end_year=2020)

    assert unmapped.empty
    yem_2015 = std[(std["iso3"] == "YEM") & (std["year"] == 2015)]["battle_deaths"].iloc[0]
    syr_2016 = std[(std["iso3"] == "SYR") & (std["year"] == 2016)]["battle_deaths"].iloc[0]
    assert float(yem_2015) == 15.0
    assert float(syr_2016) == 7.0

