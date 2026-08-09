#!/usr/bin/env python3
"""hw-price-radar deterministic collector.

Reads skus.yaml, fetches deterministic-tier sources, appends observations to
data/prices.jsonl, rebuilds data/latest.json and data/alerts.json.

Hard rules (see CLAUDE.md): one source failing never fails the run; no Amazon
or Newegg HTML scraping; threshold values come only from THRESHOLDS_JSON env
and are never written into committed records.
"""
from __future__ import annotations
import json, os, re, sys, time, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 hw-price-radar/1.0 (+github.com/Tandem-Engineering-Group/hw-price-radar)")
TODAY = date.today().isoformat()
DRY = "--dry-run" in sys.argv

MONEY = re.compile(r"\$\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))")


def fetch(url: str, timeout: int = 25, cookie: str | None = None) -> str:
    headers = {"User-Agent": UA, "Accept-Language": "en-US"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def money_to_float(s: str) -> float:
    return float(s.replace(",", ""))


# ---------------------------------------------------------------- fetchers --
def shopify_json(src: dict) -> dict:
    store, handle = src["store"].rstrip("/"), src.get("handle", "")
    try:
        doc = json.loads(fetch(f"{store}/products/{handle}.json"))
    except Exception:
        doc = None
    if doc is None:  # fallback: search the public catalog for the title
        handle = resolve_handle(store, src.get("match_title", ""))
        if not handle:
            raise RuntimeError("shopify handle unresolved")
        doc = json.loads(fetch(f"{store}/products/{handle}.json"))
    v = doc["product"]["variants"][0]
    avail = v.get("available")
    stock = None if avail is None else ("in stock" if avail else "out of stock")
    return {"price": float(v["price"]), "stock": stock,
            "note": f"handle={handle}" if handle != src.get("handle") else None}


def resolve_handle(store: str, needle: str) -> str | None:
    for page in (1, 2):
        try:
            cat = json.loads(fetch(f"{store}/products.json?limit=250&page={page}"))
        except Exception:
            return None
        for p in cat.get("products", []):
            if needle.lower() in p.get("title", "").lower():
                return p["handle"]
        if len(cat.get("products", [])) < 250:
            break
    return None


def html_regex(src: dict) -> dict:
    url, cookie, sid = src["url"], None, src.get("storeid")
    if sid:  # pin store context (Micro Center defaults to a store by egress IP)
        url += ("&" if "?" in url else "?") + f"storeID={sid}"
        cookie = f"storeSelected={sid}"
    html = fetch(url, cookie=cookie)
    window = html
    marker = src.get("price_marker")
    if marker and marker in html:
        window = html[html.index(marker): html.index(marker) + 400]
    floor, note = src.get("min_price", 100), None
    prices = [money_to_float(m) for m in MONEY.findall(window)]
    prices = [p for p in prices if p >= floor]
    if not prices:  # marker window failed — first sane price on the page
        prices = [money_to_float(m) for m in MONEY.findall(html) if money_to_float(m) >= floor]
        note = "page-scan fallback — verify"
    if not prices:
        raise RuntimeError("no price matched")
    stock = None
    if src.get("stock_regex"):
        m = re.search(src["stock_regex"], html)
        if m:
            stock = m.group(1)
            if src.get("stock_label"):
                stock += f" — {src['stock_label']}"
    return {"price": prices[0], "stock": stock, "note": note}


def listing_probe(src: dict) -> dict:
    html = fetch(src["url"])
    listed = re.search(src.get("listing_regex", "add to cart"), html, re.I)
    prices = [money_to_float(m) for m in MONEY.findall(html) if money_to_float(m) >= 500]
    return {"price": prices[0] if (listed and prices) else None,
            "stock": "LISTED" if listed else "unlisted",
            "note": "listing_probe"}


def keepa(src: dict) -> dict:
    key = os.environ.get("KEEPA_API_KEY")
    asin = src.get("asin")
    if not key or not asin:
        raise RuntimeError("keepa skipped (no key or asin)")
    doc = json.loads(fetch(
        f"https://api.keepa.com/product?key={key}&domain=1&asin={asin}&stats=1"))
    stats = doc["products"][0].get("stats") or {}
    cur = (stats.get("current") or [None])[1]  # NEW price index, keepa cents
    if cur in (None, -1):
        raise RuntimeError("keepa: no NEW price")
    return {"price": cur / 100.0, "stock": None, "note": "keepa NEW"}


METHODS = {"shopify_json": shopify_json, "html_regex": html_regex,
           "listing_probe": listing_probe, "keepa": keepa}


# -------------------------------------------------------------------- main --
def main() -> int:
    cfg = yaml.safe_load((ROOT / "skus.yaml").read_text())
    thresholds = json.loads(os.environ.get("THRESHOLDS_JSON", "{}") or "{}")
    rows, latest, alerts = [], {"as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "skus": {}}, []

    for sku in cfg["skus"]:
        entry = {"name": sku["name"], "category": sku.get("category"), "sources": [], "best": None}
        for src in sku.get("sources", []):
            if src.get("tier") == "agentic":  # no fetch — weekly Cowork sweep owns updates
                entry["sources"].append({"retailer": src["retailer"], "price": None,
                                         "stock": src.get("note"), "url": src.get("url")})
                continue
            method = METHODS.get(src.get("method", ""))
            if src.get("tier") not in ("deterministic", "keepa", "watch") or not method:
                continue
            rec = {"date": TODAY, "sku": sku["id"], "source": src["retailer"],
                   "price": None, "currency": "USD", "stock": None, "note": None}
            try:
                got = method(src)
                rec.update({k: got.get(k) for k in ("price", "stock", "note")})
                print(f"[ok]   {sku['id']:<18} {src['retailer']:<16} {rec['price']} {rec['stock'] or ''}")
            except Exception as e:
                rec["note"] = f"error: {e}"
                print(f"[skip] {sku['id']:<18} {src['retailer']:<16} {e}")
            rows.append(rec)
            entry["sources"].append({"retailer": src["retailer"], "price": rec["price"],
                                     "stock": rec["stock"], "url": src.get("url") or src.get("store")})
            if rec["price"] is not None:
                if entry["best"] is None or rec["price"] < entry["best"]["price"]:
                    entry["best"] = {"price": rec["price"], "source": src["retailer"]}
                t = thresholds.get(sku["id"])
                if t and rec["price"] <= float(t):
                    alerts.append({"sku": sku["id"], "source": src["retailer"],
                                   "price": rec["price"],
                                   "note": "below configured threshold"})
        latest["skus"][sku["id"]] = entry
        time.sleep(1.5)  # be polite between SKUs

    if DRY:
        print(json.dumps(latest, indent=2)[:2000]); return 0
    DATA.mkdir(exist_ok=True)
    with (DATA / "prices.jsonl").open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (DATA / "latest.json").write_text(json.dumps(latest, indent=1))
    (DATA / "alerts.json").write_text(json.dumps(alerts, indent=1))
    print(f"wrote {len(rows)} observations, {len(alerts)} alert(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
