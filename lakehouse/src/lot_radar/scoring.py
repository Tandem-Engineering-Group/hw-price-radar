"""SK-fit scoring. All thresholds come from config/scoring.yml -- never hardcode."""
from __future__ import annotations

import math
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "scoring.yml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def drive_minutes(lat, lon, cfg) -> int:
    d = cfg["Detroit"]
    mi = haversine_miles(lat, lon, d["Lat"], d["Lon"]) * cfg["DriveTime"]["RoadFactor"]
    return round(mi / cfg["DriveTime"]["AvgMph"] * 60)


def lake_tier(lake_name, lakes_cfg) -> str:
    if not lake_name:
        return "Other"
    if lake_name in lakes_cfg.get("Tier1", []):
        return "Tier1"
    if lake_name in lakes_cfg.get("Tier2", []):
        return "Tier2"
    return "Other"


def _parti_chips(lot: dict, rules: dict) -> tuple[dict, list]:
    flags = []
    gf = lot.get("GradeFallFt")
    fr = lot.get("FrontageFt") or 0
    facing = lot.get("ShoreFacing")

    r1 = rules["Sk1"]
    if gf is None:
        sk1 = "AMBER"
        flags.append("NeedsElevation")
    elif gf >= r1["GreenGradeFallFt"]:
        sk1 = "GREEN"
    elif gf >= r1["AmberGradeFallFt"]:
        sk1 = "AMBER"
    else:
        sk1 = "RED"

    r2 = rules["Sk2"]
    flat = gf is not None and gf <= r2["MaxFlatGradeFallFt"]
    sk2 = "GREEN" if (flat and fr >= r2["GreenFrontageFt"]) else "AMBER"

    r3 = rules["Sk3"]
    sk3 = "GREEN" if (facing in r3["GreenFacings"] and fr >= r3["GreenFrontageFt"]) else "AMBER"

    if fr and fr < 75:
        flags.append("NarrowFrontage")
    return {"Sk1": sk1, "Sk2": sk2, "Sk3": sk3}, flags


def _composite(lot: dict, cfg: dict) -> tuple[int, int, int]:
    """Composite = percent of ACHIEVABLE points from known factors.

    A factor with no data (e.g. GradeFallFt unverified) is excluded from both
    sides, so missing data never counts against a lot — check Flags instead.
    FrontageFt: null means unknown; an explicit 0 means known-no-private-frontage
    (shared/view lots) and DOES score. Returns (composite, known, total factors).
    """
    w = cfg["Weights"]
    earned = possible = known = total = 0

    def add(pts: int | None, mx: int) -> None:
        nonlocal earned, possible, known, total
        total += 1
        if pts is None:                    # factor unknown for this lot
            return
        earned += pts
        possible += mx
        known += 1

    gf = lot.get("GradeFallFt")
    gw = w["GradeFall"]
    add(None if gf is None else gw["Ge8"] if gf >= 8 else gw["Ge4"] if gf >= 4 else gw["Lt4"],
        max(gw.values()))
    fr = lot.get("FrontageFt")
    fw = w["Frontage"]
    add(None if fr is None else fw["Ge150"] if fr >= 150 else fw["Ge100"] if fr >= 100
        else fw["Ge75"] if fr >= 75 else fw["Lt75"], max(fw.values()))
    ac = lot.get("AcreageAc")
    aw = w["Acreage"]
    add(None if ac is None else aw["Ge1_5"] if ac >= 1.5 else aw["Ge0_75"] if ac >= 0.75
        else aw["Lt0_75"], max(aw.values()))
    facing = lot.get("ShoreFacing")
    add(None if not facing else w["Orientation"].get(facing, 0), max(w["Orientation"].values()))
    add(w["LakeTier"].get(lot.get("LakeTier") or "Other", 0), max(w["LakeTier"].values()))
    dm = lot.get("DriveMinsFromDetroit")
    dw = w["DriveMins"]
    add(None if dm is None else dw["Le180"] if dm <= 180 else dw["Le240"] if dm <= 240
        else dw["Le300"] if dm <= 300 else dw["Gt300"], max(dw.values()))
    budget = cfg["Budget"]["MaxPriceUsd"]
    if budget:                             # factor exists only when a budget is configured
        add(None if not lot.get("PriceUsd")
            else w["PriceUnderBudget"] if lot["PriceUsd"] <= budget else 0,
            w["PriceUnderBudget"])
    for weight_key, lot_key in (("Utilities", "UtilitiesBand"),
                                ("Growth", "GrowthBand"),
                                ("Tax", "TaxBand")):
        if weight_key in w:
            band = lot.get(lot_key)
            add(None if not band else w[weight_key].get(band, 0), max(w[weight_key].values()))
    pf = w.get("PricePerFrontFt")
    if pf:
        price = lot.get("PriceUsd")
        if price and fr:
            ppf = price / fr
            add(pf["Le3000"] if ppf <= 3000 else pf["Le5000"] if ppf <= 5000 else pf["Gt5000"],
                max(pf.values()))
        else:
            add(None, max(pf.values()))
    if not possible:
        return 0, known, total
    return round(100 * earned / possible), known, total


def score_lot(lot: dict, cfg: dict, lakes_cfg: dict) -> dict:
    """Mutates and returns lot with LakeTier, DriveMinsFromDetroit, Scores, Flags."""
    lot["LakeTier"] = lake_tier(lot.get("LakeName"), lakes_cfg)
    if lot.get("DriveMinsFromDetroit") is None and lot.get("Lat") and lot.get("Lon"):
        lot["DriveMinsFromDetroit"] = drive_minutes(lot["Lat"], lot["Lon"], cfg)
    chips, flags = _parti_chips(lot, cfg["PartiRules"])
    composite, known, total = _composite(lot, cfg)
    lot["Scores"] = {**chips, "Composite": composite,
                     "FactorsKnown": known, "FactorsTotal": total}
    lot["Flags"] = sorted(set(lot.get("Flags", []) + flags))
    return lot
