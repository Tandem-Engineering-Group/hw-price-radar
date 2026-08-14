# CLAUDE.md — hw-price-radar

## Mission
Automated daily price + availability tracker for AI workstation hardware TEG is
evaluating (Strix Halo minis, RTX PRO Blackwell GPUs, RTX Spark N1X boxes).
GitHub Actions cron collects prices → commits history → deploys a Pages
dashboard readable from a phone. Zero servers, zero local dependencies.

Dashboard: https://tandem-engineering-group.github.io/hw-price-radar/

## Architecture (two tiers — do not blur them)
1. **Deterministic tier** (`src/collect.py`, runs daily via Actions cron)
   - Shopify JSON endpoints (Minisforum): `{store}/products/{handle}.json` — clean, public, stable.
   - Simple HTML fetch + regex (Micro Center, CompSource, B&H): tolerate breakage, never fail the run.
   - Keepa API (Amazon) — only if `KEEPA_API_KEY` secret exists. NEVER scrape Amazon HTML.
2. **Agentic tier** (weekly Cowork scheduled task, lives OUTSIDE this repo)
   - Newegg prices, GR1X/EdgeMesa preorder detection, news. Commits notes to `data/agent-notes/`
     via GitHub connector. Anything needing judgment goes here, not in collect.py.

## Hard rules
- NO per-site scrapers for Newegg or Amazon HTML. Both bot-wall GitHub's IP ranges;
  brittle scrapers are worse than no data. Amazon = Keepa. Newegg = agentic tier.
- NO secrets in the repo. `KEEPA_API_KEY`, `THRESHOLDS_JSON`, `TEAMS_WEBHOOK_URL`
  live in Actions secrets only.
- NO procurement intent in this public repo: no unit quantities, no budget ceilings,
  no threshold values in code, YAML, README, or committed alert records.
  Alert records say "below configured threshold" — never the number.
- A collector failure for one source logs and continues. The run must always
  commit whatever it got. Partial data > no data.
- Data commits use message `data: daily price snapshot [skip ci]`.

## Data contracts
- `data/prices.jsonl` — append-only. One record per source observation:
  `{"date","sku","source","price","currency","stock","note"}`
  (`price` null when unlisted/unfetchable; `stock` free text like "in stock — Madison Heights".)
- `data/latest.json` — full snapshot rebuilt each run: `{as_of, skus:{<id>:{name, category, best:{price,source}, sources:[...]}}}`
- `data/alerts.json` — rebuilt each run; empty array when nothing fires.
- `data/stats.json` — rebuilt each run from prices.jsonl history: per SKU
  `{floor, floor90, median90, trend_month, proj30:{date,price}, references:{...}}`.
  Rows whose note contains "verify" are excluded from floors/trends. `references`
  come from an optional per-SKU `references:` block in skus.yaml (launch_price,
  analyst_est) — public market facts only, NEVER our willingness-to-pay.
- `data/agent-notes/*.md` — written by the weekly agentic sweep. The deploy step
  copies them into the Pages artifact with a generated `index.json` manifest
  (newest-first); the dashboard renders the newest 3 as a "Field notes" strip.
- Dashboard (`site/index.html`) reads `data/latest.json` + `data/prices.jsonl` +
  `data/stats.json` at relative path `data/…` (workflow copies `data/` into the
  Pages artifact). Charts need Chart.js + chartjs-adapter-date-fns from cdnjs;
  the page must fully render without them.

## Backlog for Claude Code (in order)
1. Run `python src/collect.py --dry-run` locally; confirm the Shopify handle
   resolver finds the MS-S1 MAX on store.minisforum.com (fallback search is
   implemented — verify and pin the resolved handle into skus.yaml).
2. Trigger `daily-prices.yml` via workflow_dispatch; confirm data commit +
   Pages deploy both green; open the dashboard on mobile.
3. Add optional Teams alert step: if `data/alerts.json` non-empty AND
   `TEAMS_WEBHOOK_URL` secret exists, POST a summary card (jarvis-comms pattern).
4. Harden Micro Center stock detection across storeids (055 = Madison Heights).
5. When GR1X/EdgeMesa get real product/retail pages, promote them from
   `watch` tier to deterministic sources.

## Conventions
- Python 3.12, stdlib + pyyaml only. No headless browsers, no selenium.
- Keep collect.py under ~250 lines; complexity budget is deliberately small.
- Dashboard is one file (`site/index.html`), Chart.js from cdnjs, no build step.
- `site/` may also carry standalone sibling pages published at their own URL
  (currently `site/bahamas/` → `/hw-price-radar/bahamas/`). They are self-contained,
  share no code or data with the radar, and are out of scope for collect.py.
