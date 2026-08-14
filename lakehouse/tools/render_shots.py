"""Generate SK-set concept renders via the Gemini image API ("nano banana").

Runs in the lakehouse-renders GitHub Action, where the runner has open internet
and GEMINI_API_KEY lives in Actions secrets — never in the repo. Shots and
prompts come from config/render-shots.yml; output goes to site/lakehouse/renders/
as JPEG (Pillow, an Actions-only dep) or PNG when Pillow is absent, plus an
index.json manifest the portal page reads to populate its render strip.

Fail-soft per shot: a failed generation logs and continues; the manifest always
reflects exactly what exists on disk, so hand-dropped renders named <shot-id>.jpg
are picked up too (run with --manifest-only to index those without generating).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]                     # lakehouse/
CONFIG = ROOT / "config" / "render-shots.yml"
OUT = ROOT.parent / "site" / "lakehouse" / "renders"
MODEL = "gemini-2.5-flash-image"
API = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def generate(prompt: str, key: str, aspect: str) -> bytes | None:
    gen_cfg = {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}
    for attempt in (0, 1):
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_cfg if attempt == 0 else {"responseModalities": ["IMAGE"]}}
        req = urllib.request.Request(
            API, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.load(r)
            for part in out["candidates"][0]["content"]["parts"]:
                blob = part.get("inlineData") or part.get("inline_data")
                if blob:
                    return base64.b64decode(blob["data"])
            print("  no image part in response", file=sys.stderr)
            return None
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode(errors="replace")
            print(f"  HTTP {e.code}: {detail}", file=sys.stderr)
            if e.code == 400 and attempt == 0:
                continue                      # older API surface: retry without imageConfig
            return None
        except Exception as e:                # noqa: BLE001 — fail-soft per shot
            print(f"  {type(e).__name__}: {e}", file=sys.stderr)
            return None
    return None


def save(raw: bytes, stem: str) -> Path:
    try:
        from io import BytesIO
        from PIL import Image
        path = OUT / f"{stem}.jpg"
        Image.open(BytesIO(raw)).convert("RGB").save(path, "JPEG", quality=88, optimize=True)
    except ImportError:
        path = OUT / f"{stem}.png"
        path.write_bytes(raw)
    return path


def write_manifest(shots: list[dict]) -> list[dict]:
    on_disk = {p.stem: p.name for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp")
               for p in OUT.glob(ext)}
    manifest = [{"file": on_disk[s["Id"]], "scheme": s["Scheme"], "label": s["Label"]}
                for s in shots if s["Id"] in on_disk]
    (OUT / "index.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tier", choices=["hero", "full"], default="hero")
    ap.add_argument("--only", help="comma-separated shot Ids, overrides --tier")
    ap.add_argument("--manifest-only", action="store_true",
                    help="rebuild index.json from files on disk; no generation")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    shots = cfg["Shots"]
    OUT.mkdir(parents=True, exist_ok=True)

    if not args.manifest_only:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            print("GEMINI_API_KEY not set", file=sys.stderr)
            return 1
        if args.only:
            wanted = {s.strip() for s in args.only.split(",")}
            todo = [s for s in shots if s["Id"] in wanted]
        else:
            todo = [s for s in shots if args.tier == "full" or s["Tier"] == "hero"]
        done = 0
        for shot in todo:
            print(f"{shot['Id']} — {shot['Scheme']} {shot['Label']}")
            raw = generate(f"{cfg['Base']} {shot['Prompt']}", key, cfg["AspectRatio"])
            if raw:
                path = save(raw, shot["Id"])
                print(f"  wrote {path.name} ({path.stat().st_size:,} bytes)")
                done += 1
            time.sleep(2)                     # politeness between calls
        if todo and not done:
            print("every requested shot failed — check the key/model", file=sys.stderr)
            write_manifest(shots)
            return 1
        print(f"generated {done}/{len(todo)} shot(s)")

    manifest = write_manifest(shots)
    print(f"manifest: {len(manifest)} render(s) indexed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
