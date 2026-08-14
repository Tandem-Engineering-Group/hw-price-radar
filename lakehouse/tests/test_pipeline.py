import json

from lot_radar.pipeline import run

WATCHLIST = """
Lots:
  - Placeholder: true
    SourceUrl: "TODO-should-be-excluded"
    Lat: 44.9
    Lon: -85.3
  - SourceUrl: "https://example.com/listing/1"
    Name: Test Lot
    LakeName: Torch Lake
    County: Antrim
    Lat: 44.94
    Lon: -85.31
    PriceUsd: 400000
    AcreageAc: 1.2
    FrontageFt: 150
    ShoreFacing: W
    UtilitiesBand: Partial
    GrowthBand: High
    TaxBand: Low
"""


def _setup(tmp_path):
    wl = tmp_path / "watchlist.yml"
    wl.write_text(WATCHLIST)
    return wl, tmp_path / "data", tmp_path / "site.json"


def test_pipeline_excludes_placeholders_and_scores(tmp_path):
    wl, data, site = _setup(tmp_path)
    out = run(today="2026-08-14", watchlist=wl, data_dir=data, site_json=site)
    assert len(out["Lots"]) == 1
    lot = out["Lots"][0]
    assert lot["Scores"]["Composite"] > 0
    assert lot["FirstSeen"] == lot["LastSeen"] == "2026-08-14"
    assert lot["PriceHistory"] == [{"Date": "2026-08-14", "PriceUsd": 400000}]
    assert json.loads(site.read_text())["AsOf"] == "2026-08-14"
    assert (data / "history" / "2026-08-14.json").exists()


def test_pipeline_merge_keeps_firstseen_and_tracks_price(tmp_path):
    wl, data, site = _setup(tmp_path)
    run(today="2026-08-14", watchlist=wl, data_dir=data, site_json=site)
    wl.write_text(WATCHLIST.replace("PriceUsd: 400000", "PriceUsd: 375000"))
    out = run(today="2026-08-21", watchlist=wl, data_dir=data, site_json=site)
    lot = out["Lots"][0]
    assert lot["FirstSeen"] == "2026-08-14"
    assert lot["LastSeen"] == "2026-08-21"
    assert lot["PriceHistory"][-1] == {"Date": "2026-08-21", "PriceUsd": 375000}
