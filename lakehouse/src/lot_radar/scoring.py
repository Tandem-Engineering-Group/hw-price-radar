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


def _composite(lot: dict, cfg: dict) -> int:
    w = cfg["Weights"]
    pts = 0
    gf = lot.get("GradeFallFt")
    if gf is not None:
        pts += w["GradeFall"]["Ge8"] if gf >= 8 else w["GradeFall"]["Ge4"] if gf >= 4 else w["GradeFall"]["Lt4"]
    fr = lot.get("FrontageFt") or 0
    fw = w["Frontage"]
    pts += fw["Ge150"] if fr >= 150 else fw["Ge100"] if fr >= 100 else fw["Ge75"] if fr >= 75 else fw["Lt75"]
    ac = lot.get("AcreageAc") or 0
    aw = w["Acreage"]
    pts += aw["Ge1_5"] if ac >= 1.5 else aw["Ge0_75"] if ac >= 0.75 else aw["Lt0_75"]
    pts += w["Orientation"].get(lot.get("ShoreFacing") or "N", 0)
    pts += w["LakeTier"].get(lot.get("LakeTier") or "Other", 0)
    dm = lot.get("DriveMinsFromDetroit")
    if dm is not None:
        dw = w["DriveMins"]
        pts += dw["Le180"] if dm <= 180 else dw["Le240"] if dm <= 240 else dw["Le300"] if dm <= 300 else dw["Gt300"]
    budget = cfg["Budget"]["MaxPriceUsd"]
    if budget and lot.get("PriceUsd") and lot["PriceUsd"] <= budget:
        pts += w["PriceUnderBudget"]
    return min(pts, 100)


def score_lot(lot: dict, cfg: dict, lakes_cfg: dict) -> dict:
    """Mutates and returns lot with LakeTier, DriveMinsFromDetroit, Scores, Flags."""
    lot["LakeTier"] = lake_tier(lot.get("LakeName"), lakes_cfg)
    if lot.get("DriveMinsFromDetroit") is None and lot.get("Lat") and lot.get("Lon"):
        lot["DriveMinsFromDetroit"] = drive_minutes(lot["Lat"], lot["Lon"], cfg)
    chips, flags = _parti_chips(lot, cfg["PartiRules"])
    lot["Scores"] = {**chips, "Composite": _composite(lot, cfg)}
    lot["Flags"] = sorted(set(lot.get("Flags", []) + flags))
    return lot
