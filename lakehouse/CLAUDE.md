# CLAUDE.md — lakehouse (northern Michigan cabin planning)

## Hosting (temporary)

This section lives inside the public `hw-price-radar` repo for now: project files under
`lakehouse/`, public portal under `site/lakehouse/` (published at
`/hw-price-radar/lakehouse/` by the host repo's existing Pages deploy — `daily-prices.yml`
copies all of `site/` into the artifact). It shares the Pages site only — no code or data
with the price radar, and collect.py never touches it. It will migrate to its own repo
later: keep every reference inside `lakehouse/` + `site/lakehouse/` +
`.github/workflows/lot-radar-weekly.yml` so migration is a directory move.

All paths below are relative to `lakehouse/` unless they start with `site/` or `.github/`.

## Mission

Two concerns, one personal project (split later if either grows):

1. **SK Concept Archive** (`docs/sk-set/`) — the three A-frame hybrid partis for a northern
   Michigan lakehouse (SK-1 Stacked Chalet, SK-2 A + Bar, SK-3 Kicked Ridge). Static
   reference: deck, diagrams, render prompt pack. Nothing to build; this is design context
   for everything below.
2. **Lot Radar** — automated weekly discovery + scoring of lakefront lots on Michigan
   INTERIOR lakes statewide (northern tier + downstate; Great Lakes frontage out of
   scope), published to a static GitHub Pages dashboard. The radar's job is to answer
   the open design question: **which parti does the land want?** SK-1 needs 8–10 ft of
   grade fall to the water; SK-2 wants a wide flat lot; SK-3 wants a view axis. The
   scoring engine encodes exactly that.

Owner: Richard Letts. Cadence: weekly cron, Monday 06:00 ET. Status vocabulary:
GREEN / AMBER / RED. Schema fields: PascalCase. Phases end in **STOP gates** — do not
proceed past a gate without explicit approval in chat.

## Non-negotiables

- **Polite acquisition only.** Respect robots.txt and ToS. Max 1 request / 2 s per host,
  identify with a real UA string, cache aggressively. If a source blocks or requires
  anti-bot evasion: do **not** fight it — degrade that source to `watchlist` mode, flag
  it AMBER in the dashboard footer, and move on. Manual watchlist mode must always work
  even if every adapter is dead.
- **No paid APIs, no secrets** without explicit approval. Free tiers only (USGS EPQS,
  OSM Overpass, OSM tiles / OpenFreeMap).
- **No fabricated listings.** Seed entries in `config/watchlist.yml` are marked
  PLACEHOLDER and exist only to exercise the pipeline; they are excluded from the
  published dashboard until replaced with real listing URLs.
- **Static everything.** No servers. Pipeline runs in Actions, output is JSON + a static
  site. The host repo and its Pages site are **already public** — everything committed
  here must be publishable: public-listing data, scores, and design concepts only.
- **No willingness-to-pay numbers in the repo** (host-repo rule, same spirit as its
  hardware thresholds): `Budget.MaxPriceUsd` in `config/scoring.yml` stays `null` in
  committed files. If a real price cap is ever wanted, it moves to an Actions secret or
  stays local — never committed.
- **PascalCase** for all data fields. `LotId`, `GradeFallFt`, `DriveMinsFromDetroit`.
- Python 3.12, `requests` + `PyYAML` + `pytest` only unless a phase justifies more.

## Data model (`src/lot_radar/schema.py` — already implemented)

Lot record:

| Field | Type | Notes |
|---|---|---|
| LotId | str | stable hash of SourceUrl |
| Source | str | adapter name or `watchlist` |
| SourceUrl | str | canonical listing URL |
| FirstSeen / LastSeen | ISO date | maintained by pipeline diff |
| Status | enum | Active / Pending / Sold / Delisted |
| PriceUsd | int? | |
| PriceHistory | list[{Date, PriceUsd}] | appended on change |
| AcreageAc / FrontageFt | float? | |
| LakeName / LakeTier / County / Township | str? | LakeTier from `config/lakes.yml` |
| Lat / Lon | float | required for enrichment |
| RoadElevationFt / ShoreElevationFt / GradeFallFt | float? | Phase 2 |
| ShoreFacing | str? | one of N/NE/E/SE/S/SW/W/NW; manual override allowed |
| DriveMinsFromDetroit | int? | from 1 Park Ave, Detroit (42.3355, -83.0508) |
| Scores | {Sk1, Sk2, Sk3, Composite} | Sk* are GREEN/AMBER/RED; Composite 0–100 |
| Flags | list[str] | e.g. NeedsElevation, NarrowFrontage, AdapterStale |
| Notes | str | |

Persistent store: `data/lots.json` (current state) + `data/history/YYYY-MM-DD.json`
(weekly snapshots). Diff between runs drives the "This Week" panel: New / Price Drop /
Pending / Gone.

## Scoring (implemented in `src/lot_radar/scoring.py`, thresholds in `config/scoring.yml`)

Per-parti chips:

- **Sk1 (Stacked Chalet):** GradeFallFt ≥ 8 → GREEN; 4–8 → AMBER; < 4 → RED;
  missing → AMBER + `NeedsElevation`.
- **Sk2 (A + Bar):** GradeFallFt ≤ 4 AND FrontageFt ≥ 120 → GREEN; buildable otherwise →
  AMBER. Flat, wide land is this parti's friend.
- **Sk3 (Kicked Ridge):** ShoreFacing ∈ {W, SW, NW} AND FrontageFt ≥ 100 → GREEN;
  else AMBER. The kick wants a sunset axis.

Composite (0–100): grade-fall band + frontage band + acreage + orientation + lake tier +
drive-time band + price sanity. Exact weights live in `config/scoring.yml` — tune there,
never hardcode. Unit tests in `tests/test_scoring.py` pin the bands; keep them green.

## Enrichment (Phase 2)

- **Elevation:** USGS EPQS, `https://epqs.nationalmap.gov/v1/json?x={lon}&y={lat}&units=Feet`
  — free, keyless. Sample the parcel point (road side) and the nearest shore point;
  GradeFallFt = RoadElevationFt − ShoreElevationFt. Client stub exists in
  `src/lot_radar/enrich/elevation.py` — **written blind, validate live before trusting.**
- **Shore geometry:** OSM Overpass — nearest `natural=water` polygon edge gives the shore
  point and an approximate ShoreFacing (normal of nearest edge, pointing at water).
  Manual `ShoreFacing` in watchlist overrides computed.
- **Drive time v0:** haversine miles × RoadFactor ÷ AvgMph (config). Good enough to band.

## Discovery adapters (Phase 4 — highest breakage risk, build last)

Interface in `src/lot_radar/adapters/__init__.py`: `discover(config) -> list[RawListing]`.
One module per source, each with cached HTML fixtures + parse tests. Candidate order:

1. `landwatch` — MI lakefront-lot search pages
2. `landandfarm`
3. `land_com`
4. `zillow_lots` — expect anti-bot; attempt once, degrade gracefully

Search scope: waterfront **lots/land** (not homes), counties in `config/counties.yml`,
price cap from `config/scoring.yml`. Every adapter failure = AMBER flag in dashboard
footer with LastGoodRun date, never a crashed pipeline.

## Dashboard (Phase 3 — first cut LIVE)

Single static page in `site/lakehouse/` with two tabs: **SK Set** (concept sheet set +
render strip) and **Lot Map** (Leaflet CDN + OSM tiles; weekly top-10 markers colored by
composite band, popup links to the live listing, sortable-enough table below). Reads
`data.json` (written by the pipeline) at a relative path. No build step; the page must
still fully render if CDNs are blocked — the table works without Leaflet. Reuses the SK
drafting aesthetic: vellum `#EFEDE6`, ink `#1C1B18`, graphite `#6E6A61`, redline
`#C2401B` for flags/watch-outs, lake `#3E7C96`. Monospace labels, sheet-border framing —
match `docs/sk-set/aframe-hybrid-concept-partis.html`.

Components: This Week panel (new / drops / gone) · filter bar (county, lake, price max,
"SK-1 viable" toggle = GradeFallFt ≥ 8, frontage min) · sortable table · Leaflet map with
GREEN/AMBER/RED markers · lot detail card with per-parti chips and a link out to the
listing. Footer: adapter health + LastRun timestamp.

## Concept renders (live now, separate from the phase plan)

`config/render-shots.yml` (prompts from `docs/sk-set/lakehouse-render-prompt-pack.md`) +
`tools/render_shots.py` + `.github/workflows/lakehouse-renders.yml`. Generation runs
**only in Actions** — this repo's Claude sandbox egress blocks every image API, but
runners have open internet. Two engines: `sdxl` (default — SDXL-Turbo open weights on
the runner CPU, keyless, weights cached between runs) and `gemini` (nano banana,
better quality, opt-in; `GEMINI_API_KEY` from Google AI Studio lives in Actions
secrets only). Output: `site/lakehouse/renders/*.jpg` + `index.json` manifest; the
portal's render strip populates from the manifest and the page fully renders without
it. Fail-soft per shot. Hand-dropped renders named `<shot-id>.jpg` in that folder get
indexed by `python tools/render_shots.py --manifest-only`.

## Pipeline (`src/lot_radar/pipeline.py`, Phase 1–5)

discover → normalize → merge/diff against `data/lots.json` → enrich (only lots missing
enrichment; cache forever) → score → write data + snapshot → render `site/lakehouse/data.json`
→ (Phase 5) commit + open a GitHub Issue "Lot Radar — week of {date}" with the This Week
digest so the phone gets a native notification. No Pages deploy job of its own: a push
touching `site/**` triggers the host repo's deploy automatically.

## Weekly sweep (live) — how the 10 lots stay fresh

A weekly claude.ai Routine (Mondays, fresh session) does the judgment work no adapter
can: re-verify each watchlist lot via WebSearch (listing pages are egress-blocked from
the session — snippets only, facts never invented), update prices/Status/LastVerified,
hunt replacements, keep ~20 Active lots (statewide interior lakes — cover northern tier
AND downstate each sweep), then run pytest + the pipeline and ship via PR. Conventions it must keep: FrontageFt is PRIVATE frontage only; ApproxLocation /
SharedFrontage / NotWaterfront / WaterfrontUnverified / MayHaveStructure /
PriceOnInquiry / IndexUrlOnly flags; bands per scoring.yml comments; lower price on
conflicts, noted. The `lot-radar-weekly.yml` Action stays dispatch-only (rescore
without discovery) until Phase 5 replaces the Routine.

## Phase plan — STOP at every gate

- **Phase 0 — Verify scaffold.** ✅ done (2026-08-14): tests green.
- **Phase 1 — Pipeline core on seeds.** ✅ done (2026-08-14): `pipeline.py` runs
  watchlist → merge/diff → score → `data/lots.json` + history snapshot +
  `site/lakehouse/data.json`. Watchlist now carries 10 REAL curated listings
  (placeholders retired).
- **Phase 2 — Live enrichment.** Validate EPQS on 2–3 known points (e.g. a Torch Lake
  shore point vs a point 500 ft inland — sanity: shore ≈ 590 ft ASL). Wire Overpass shore
  lookup + drive-time calc. Re-score seeds. **STOP: confirm GradeFallFt numbers look sane.**
- **Phase 3 — Dashboard.** ✅ first cut done (2026-08-14): Lot Map tab live with real
  data. Remaining: filter bar, This Week diff panel, lot detail cards.
- **Phase 4 — Adapters.** One source at a time, fixture-tested, politeness rules above.
  **STOP after each adapter with sample discoveries.**
- **Phase 5 — Automation.** Uncomment the cron in `.github/workflows/lot-radar-weekly.yml`, add the
  weekly Issue digest, run one full cycle manually. **DONE → steady state.**

## Steady state

Weekly run Monday 06:00 ET. Human reviews the Issue digest, promotes interesting lots by
adding notes/`ShoreFacing` overrides in watchlist, retires dead ones. When a lot goes
serious: pull its parcel from county GIS, run the SK partis through Forma on it, and the
winning parti graduates to Revit per the deck (`docs/sk-set/`).
