"""Discovery adapter interface -- Phase 4.

Each adapter module exposes:
    discover(config: dict) -> list[dict]   # raw listings, normalized keys
Rules (see CLAUDE.md Non-negotiables): robots.txt respected, >=2s between requests,
real UA, cache fixtures under data/cache/, fail soft -> return [] and set an
AdapterStale flag rather than raising.
"""
