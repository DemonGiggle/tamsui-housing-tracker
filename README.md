# Tamsui Housing Tracker

MVP for long-term Tamsui housing market tracking, now oriented around monthly baseline tracking first.

## Goals

Track long-term price trends for:
- Tamsui sub-areas (e.g. 淡海新市鎮、竹圍、紅樹林、淡水站周邊)
- watched communities/buildings such as 摩納哥社區
- nearby communities around a focal building/community
- price observations grouped by layout type, so 套房 / 2房 / 3房 are not mixed together

## MVP scope

- local JSON dataset
- baseline-first monthly tracking
- simple update script for manual observations
- static HTML dashboard
- community watchlist
- layout-based grouping for more realistic price comparison
- nearby-community slots for focal projects
- ready for cron automation later

## Structure

- `data/observations.json` — raw observation log
- `data/watchlist.json` — watched regions/communities/layout types/nearby communities
- `scripts/add_observation.py` — append one observation
- `scripts/import_real_samples.py` — import verifiable public samples from lightweight public sources
- `scripts/build_dashboard.py` — generate static dashboard HTML
- `scripts/update_all.py` — canonical pipeline entrypoint; can optionally run public-source import first
- `docs/index.html` — generated dashboard

## Current watched nearby communities

For the current geography-first shortlist, Monaco (摩納哥社區) is paired with these nearby communities:
- 水立方
- 托斯卡尼翡冷翠
- 托斯卡尼麥迪奇名家
- 荷雅名人館
- 荷雅時尚館
- 尚海
- 清淞
- 高第

This list is intentionally geography-first: nearby communities around the 淡金路38巷 / surrounding block area, used as a working local observation cluster.

## Example usage

Add one observed listing:

```bash
python3 scripts/add_observation.py \
  --type listing \
  --region 淡海新市鎮 \
  --community 宏盛新世界 \
  --layout-type 2房 \
  --rooms 2 \
  --total-price 1388 \
  --unit-price 39.8 \
  --size-ping 34.9 \
  --source manual \
  --note "Example observation"
```

Rebuild dashboard only:

```bash
python3 scripts/build_dashboard.py
```

Run the canonical refresh pipeline:

```bash
python3 scripts/update_all.py
```

Run importer first, then rebuild everything:

```bash
python3 scripts/update_all.py --import-real
```

## Notes

This MVP is intentionally simple. It is designed to start collecting structured housing observations first, then evolve into automated scraping, charts, alerts, and richer market analysis.

## Baseline-first direction

Current working direction: prioritize collecting a monthly baseline for each community × layout pair.

In this project, baseline is **not fake transaction data**. It is a monthly reference point built from incomplete but grounded public information, such as community summary pricing, layout ranges, and limited verifiable samples. For the current use case, that baseline layer is already useful enough to track monthly price position and direction over time.
