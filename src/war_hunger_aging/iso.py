from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import pycountry


_NAME_OVERRIDES: dict[str, str] = {
    "SYRIAN ARAB REPUBLIC": "SYR",
    "YEMEN, REP.": "YEM",
    "UKRAINE": "UKR",
    "BOLIVIA (PLURINATIONAL STATE OF)": "BOL",
    "VENEZUELA (BOLIVARIAN REPUBLIC OF)": "VEN",
    "RUSSIAN FEDERATION": "RUS",
    "IRAN (ISLAMIC REPUBLIC OF)": "IRN",
    "LAO PEOPLE'S DEMOCRATIC REPUBLIC": "LAO",
    "VIET NAM": "VNM",
    "KOREA, REP.": "KOR",
    "KOREA, DEM. PEOPLE'S REP.": "PRK",
    "COTE D'IVOIRE": "CIV",
    "CÔTE D'IVOIRE": "CIV",
    "UNITED STATES": "USA",
    "UNITED STATES OF AMERICA": "USA",
    "BOSNIA AND HERZEGOVINA": "BIH",
}


def normalize_country_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name.upper()


@lru_cache(maxsize=2048)
def iso3_from_name(name: str) -> Optional[str]:
    key = normalize_country_name(name)
    if key in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[key]
    try:
        country = pycountry.countries.lookup(name)
    except LookupError:
        return None
    return getattr(country, "alpha_3", None)


def iso3_from_code(code: str) -> Optional[str]:
    code = code.strip().upper()
    if len(code) == 3 and code.isalpha():
        return code
    if len(code) == 2 and code.isalpha():
        try:
            c = pycountry.countries.get(alpha_2=code)
        except LookupError:
            c = None
        return getattr(c, "alpha_3", None) if c else None
    return None


def ensure_iso3(code_or_name: str) -> str:
    code_or_name = str(code_or_name).strip()
    code = iso3_from_code(code_or_name)
    if code:
        return code
    mapped = iso3_from_name(code_or_name)
    if mapped:
        return mapped
    raise ValueError(f"Could not map country '{code_or_name}' to ISO3.")

