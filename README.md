# hw-price-radar

Automated daily price + availability tracker for AI workstation hardware
(Strix Halo minis, RTX PRO Blackwell GPUs, RTX Spark N1X boxes).
GitHub Actions cron → committed price history → GitHub Pages dashboard.

**Dashboard:** https://tandem-engineering-group.github.io/hw-price-radar/

**Also published here:** [Bahamas Grid Portal](https://tandem-engineering-group.github.io/hw-price-radar/bahamas/) — a standalone
single-file grid-intelligence portal (`site/bahamas/`). Unrelated to price tracking;
it shares the Pages site only, not the data pipeline.

**And:** [Lakehouse Planning Portal](https://tandem-engineering-group.github.io/hw-price-radar/lakehouse/) — personal
northern-Michigan cabin planning breakout (`site/lakehouse/` portal, `lakehouse/`
project). Also pipeline-unrelated; self-contained and slated to migrate to its own
repo eventually. See `lakehouse/CLAUDE.md`.

## How it works
- `skus.yaml` — the watchlist. Each source is tagged with a tier.
- `src/collect.py` — deterministic tier. Runs daily at 13:17 UTC (~9:17am Detroit)
  via `.github/workflows/daily-prices.yml`: Shopify JSON (Minisforum), HTML
  fetch + regex (Micro Center / CompSource / B&H), Keepa API (Amazon, optional).
  Appends `data/prices.jsonl`, rebuilds `data/latest.json` + `data/alerts.json`,
  commits, then deploys the dashboard with the fresh data folder.
- **Agentic tier** — a weekly Claude Cowork scheduled task handles what needs
  judgment (Newegg prices, GR1X/EdgeMesa preorder detection, market news) and
  commits notes to `data/agent-notes/`. Deliberately not in this repo's code.
- `site/index.html` — single-file dashboard (Chart.js + date-fns adapter, both
  from cdnjs). Board grouped by category (buy targets / GPU / watching /
  reference), a full-width market timeline of best observed price per day,
  stepped "price tape" sparklines with observation dots, gaps for unobserved
  ranges and a dashed 30-day trend projection, per-card buy context
  (floor · 90-day median · trend, from `data/stats.json` — history-derived
  only), best-price ticker colored by 30-day trend, alert banner, per-retailer
  rows, and a "Field notes" strip fed by `data/agent-notes/*.md`. Mobile-first.

## Setup (once)
1. Settings → Pages → Source = **GitHub Actions**. *(done)*
2. Actions secrets (Settings → Secrets and variables → Actions), all optional:
   - `KEEPA_API_KEY` — enables Amazon tracking (keepa.com API, paid tiers exist).
   - `THRESHOLDS_JSON` — e.g. `{"ms-s1-max-128": 0000, "rtx-pro-5000-48": 0000}`.
     Numbers live **only** here; committed alerts never include them.
   - `TEAMS_WEBHOOK_URL` — posts an alert card to a Teams channel when alerts fire.
3. Push this scaffold, then Actions → **daily-prices** → *Run workflow* once.
4. Open the dashboard. Seed history (labeled `manual-seed`) gives the charts
   shape from day one; live rows accumulate on top of it.

## Local dry run
```
pip install pyyaml
python src/collect.py --dry-run
```

## Notes
- One source failing never fails the run — blanks mean "unfetched," not "gone."
- No Newegg/Amazon HTML scraping, ever (bot walls; Keepa covers Amazon).
- Public repo: no procurement quantities, budgets, or threshold values in
  committed files. See CLAUDE.md for the full rules and the Claude Code backlog.
