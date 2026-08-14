"""Pipeline core: watchlist -> normalize -> merge/diff -> score -> data + site JSON.

Seeds-only for now (no network): every lot comes from config/watchlist.yml, which
the weekly sweep curates by hand from real listing URLs. Placeholder entries are
excluded from all output. Merging against the previous data/lots.json maintains
FirstSeen / LastSeen / PriceHistory; a dated snapshot lands in data/history/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from lot_radar.schema import Lot
from lot_radar.scoring import load_config, score_lot

ROOT = Path(__file__).resolve().parents[2]                 # lakehouse/
WATCHLIST = ROOT / "config" / "watchlist.yml"
LAKES = ROOT / "config" / "lakes.yml"
DATA = ROOT / "data"
SITE_JSON = ROOT.parent / "site" / "lakehouse" / "data.json"


def run(today: str | None = None, watchlist: Path = WATCHLIST,
        data_dir: Path = DATA, site_json: Path = SITE_JSON) -> dict:
    today = today or date.today().isoformat()
    cfg = load_config()
    lakes = yaml.safe_load(LAKES.read_text())
    entries = yaml.safe_load(watchlist.read_text())["Lots"]

    prev = {}
    lots_path = data_dir / "lots.json"
    if lots_path.exists():
        prev = {l["LotId"]: l for l in json.loads(lots_path.read_text())["Lots"]}

    lots, problems = [], []
    for entry in entries:
        if entry.get("Placeholder"):
            continue
        lot = Lot.from_watchlist(entry)
        problems += [f"{lot.LotId}: {p}" for p in lot.validate()]
        d = lot.to_dict()
        old = prev.get(d["LotId"])
        d["FirstSeen"] = old["FirstSeen"] if old else today
        d["LastSeen"] = today
        if old:
            d["PriceHistory"] = old.get("PriceHistory", [])
            if d.get("PriceUsd") and old.get("PriceUsd") != d["PriceUsd"]:
                d["PriceHistory"] = d["PriceHistory"] + [
                    {"Date": today, "PriceUsd": d["PriceUsd"]}]
        elif d.get("PriceUsd"):
            d["PriceHistory"] = [{"Date": today, "PriceUsd": d["PriceUsd"]}]
        lots.append(score_lot(d, cfg, lakes))

    for p in problems:                     # log, never crash the run
        print(f"validate: {p}", file=sys.stderr)

    lots.sort(key=lambda l: -l["Scores"]["Composite"])
    out = {"AsOf": today, "Lots": lots}
    blob = json.dumps(out, indent=1) + "\n"

    data_dir.mkdir(exist_ok=True)
    (data_dir / "history").mkdir(exist_ok=True)
    lots_path.write_text(blob)
    (data_dir / "history" / f"{today}.json").write_text(blob)
    site_json.parent.mkdir(parents=True, exist_ok=True)
    site_json.write_text(blob)
    print(f"pipeline: {len(lots)} lot(s) scored, as of {today}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weekly", action="store_true",
                    help="accepted for the Actions cron; same behavior for now")
    ap.add_argument("--date", help="override run date (YYYY-MM-DD), for tests")
    args = ap.parse_args()
    run(args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
