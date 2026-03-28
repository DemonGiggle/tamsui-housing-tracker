# Data Sources Plan

## Current source

### 1) community.houseprice.tw
- Current role: primary source for community-page price/listing extraction.
- Current use in repo:
  - `scripts/fetch_latest_community_data.py`
  - raw rows stored in `data/observations.json`
- Current strengths:
  - aligns naturally with community-based watchlist
  - source URL can be retained per row
  - suitable for incremental weekly fetch
- Current limits:
  - one-source dependence
  - community coverage is incomplete
  - naming aliases may be needed

## Public-site standard going forward

For public-facing output, the project should follow these rules:
1. A community may remain on the watchlist even when data is missing.
2. Display layers should only use rows that can be explained and traced back to a source.
3. No fallback-derived rows should be used to pretend coverage exists.
4. Each raw row should remain attributable to a specific source and URL.

## Recommended next sources

### Priority A: second public housing/listing source
Goal:
- improve coverage for watchlist communities currently marked `待補資料`
- provide an additional external reference instead of relying on a single site

Suggested requirements:
- public page access without login
- stable URL per community or listing
- enough structured text to recover month / total price / unit price / layout / size
- acceptable fetch reliability for scheduled updates

### Priority B: transaction-oriented public source
Goal:
- increase credibility for public-facing market interpretation
- provide a more defensible basis than a single community listing source

Suggested requirements:
- clearly identifiable transaction month/date
- address/community matching is possible
- data can be linked or cited

### Priority C: metadata enrichment source
Goal:
- improve community alias mapping and building-level metadata
- support better cross-source matching

Useful fields:
- alternate community names
- address / lane / section variants
- building age
- layout hints

## Schema upgrades recommended before more sources

When adding more sources, prefer extending raw rows with:
- `fetched_at`
- `source`
- `source_type`
- `source_url`
- `raw_hash`
- `community_match_name`
- `community_match_confidence`
- `source_record_id` (if available)

## Operational next step

1. keep the current dashboard distinction between watchlist and data-backed communities
2. select one second source
3. add raw ingestion first
4. validate community matching on the 13-community watchlist
5. only then expose newly supported communities on charts/cards
