# lakehouse — northern Michigan cabin planning

Personal project: a new cabin on an inland lake in northern Michigan. Lives as a
**self-contained section of `hw-price-radar` for now** (shares the Pages site only,
not the price pipeline); planned to migrate to its own repo later — keep everything
under `lakehouse/` + `site/lakehouse/` so that migration is a directory move.

**Portal:** https://tandem-engineering-group.github.io/hw-price-radar/lakehouse/

Two concerns:

1. **`docs/sk-set/`** — SK concept partis (deck, diagrams, render prompt pack) for the
   A-frame hybrid: 2-car under, lakeside deck, 20-ft container pool, one 3D-printed
   curved element. The portal page renders the sheet set.
2. **Lot Radar** — weekly automated lakefront-lot discovery + SK-fit scoring, published
   to the portal. GitHub Actions cron -> JSON -> GitHub Pages. Phase-gated; not yet live.

Start here: read `CLAUDE.md`, then `KICKOFF.md`. Everything is phase-gated.

## Local test run
```
cd lakehouse
pip install -r requirements.txt
pytest -q
```
