"""USGS EPQS elevation client.

STATUS: WRITTEN BLIND -- validate live in Phase 2 before trusting (sandbox where this
was authored had no network access to nationalmap.gov). Sanity anchor: Torch Lake
surface is ~590 ft ASL.
"""
from __future__ import annotations

import time

import requests

EPQS_URL = "https://epqs.nationalmap.gov/v1/json"
UA = "lakehouse-lot-radar/0.1 (personal project; polite; contact via repo)"


def point_elevation_ft(lat: float, lon: float, retries: int = 3) -> float | None:
    for attempt in range(retries):
        try:
            r = requests.get(
                EPQS_URL,
                params={"x": lon, "y": lat, "units": "Feet", "output": "json"},
                headers={"User-Agent": UA},
                timeout=20,
            )
            r.raise_for_status()
            val = r.json().get("value")
            return float(val) if val is not None else None
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 * (attempt + 1))
    return None


def grade_fall_ft(road_pt: tuple[float, float], shore_pt: tuple[float, float]) -> float | None:
    road = point_elevation_ft(*road_pt)
    time.sleep(2)  # politeness
    shore = point_elevation_ft(*shore_pt)
    if road is None or shore is None:
        return None
    return round(road - shore, 1)
