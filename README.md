# Tamsui Housing Tracker

MVP for long-term Tamsui housing market tracking.

## Goals

Track long-term price trends for:
- Tamsui sub-areas (e.g. 淡海新市鎮、竹圍、紅樹林、淡水站周邊)
- watched communities/buildings such as 摩納哥社區
- nearby comparable communities around a focal building/community
- price observations grouped by layout type, so 套房 / 2房 / 3房 are not mixed together

## MVP scope

- local JSON dataset
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
- `scripts/build_dashboard.py` — generate static dashboard HTML
- `docs/index.html` — generated dashboard

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

Rebuild dashboard:

```bash
python3 scripts/build_dashboard.py
```

## Notes

This MVP is intentionally simple. It is designed to start collecting structured housing observations first, then evolve into automated scraping, charts, alerts, and richer market analysis.
