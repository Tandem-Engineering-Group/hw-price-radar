from pathlib import Path

import yaml

from lot_radar.scoring import load_config, score_lot

ROOT = Path(__file__).resolve().parents[1]
CFG = load_config(ROOT / "config" / "scoring.yml")
LAKES = yaml.safe_load(open(ROOT / "config" / "lakes.yml"))


def base(**kw):
    lot = {
        "LotId": "t", "Source": "watchlist", "SourceUrl": "u",
        "Lat": 44.94, "Lon": -85.31, "FrontageFt": 150,
        "AcreageAc": 1.2, "LakeName": "Torch Lake", "ShoreFacing": "W",
        "PriceUsd": 400000,
    }
    lot.update(kw)
    return lot


def test_sk1_green_needs_8ft_fall():
    lot = score_lot(base(GradeFallFt=10.0), CFG, LAKES)
    assert lot["Scores"]["Sk1"] == "GREEN"


def test_sk1_red_when_flat():
    lot = score_lot(base(GradeFallFt=1.0), CFG, LAKES)
    assert lot["Scores"]["Sk1"] == "RED"


def test_sk1_amber_and_flagged_when_unknown():
    lot = score_lot(base(), CFG, LAKES)
    assert lot["Scores"]["Sk1"] == "AMBER"
    assert "NeedsElevation" in lot["Flags"]


def test_sk2_green_flat_and_wide():
    lot = score_lot(base(GradeFallFt=2.0, FrontageFt=140), CFG, LAKES)
    assert lot["Scores"]["Sk2"] == "GREEN"


def test_sk3_green_sunset_axis():
    lot = score_lot(base(GradeFallFt=5.0, ShoreFacing="SW"), CFG, LAKES)
    assert lot["Scores"]["Sk3"] == "GREEN"


def test_sk3_amber_east_facing():
    lot = score_lot(base(ShoreFacing="E"), CFG, LAKES)
    assert lot["Scores"]["Sk3"] == "AMBER"


def test_composite_rewards_tier1_slope_frontage():
    strong = score_lot(base(GradeFallFt=10.0), CFG, LAKES)
    weak = score_lot(
        base(GradeFallFt=1.0, FrontageFt=70, AcreageAc=0.5,
             LakeName="Nowhere Lake", ShoreFacing="E"),
        CFG, LAKES,
    )
    assert strong["Scores"]["Composite"] > weak["Scores"]["Composite"]
    assert "NarrowFrontage" in weak["Flags"]


def test_drive_minutes_computed():
    lot = score_lot(base(GradeFallFt=9.0), CFG, LAKES)
    assert 150 <= lot["DriveMinsFromDetroit"] <= 320
