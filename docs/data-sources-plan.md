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


## Candidate assessment (2026-03-28)

### Recommended second source: Sinyi community pages
- Example verified pages:
  - 摩納哥: https://www.sinyi.com.tw/communitylist/communityinfo/0009663
  - 台北灣 sample page fetched successfully: https://www.sinyi.com.tw/communitylist/communityinfo/0010758
- Why this is the best current second source:
  - plain `web_fetch` text extraction already works
  - community-level pages align with the current watchlist model
  - page text includes transaction month, address/floor, total price, unit price, size, layout, building age
  - also exposes basic community metadata useful for validation
- Cautions:
  - page text is dense and may need robust parsing
  - site-specific IDs will need a community mapping layer
  - some fields may mix site-calculated metrics with official record excerpts, so raw extraction should preserve context

### Other candidates worth evaluating later
- Yungching community / evertrust pages
  - promising, but quick fetch extraction was less reliable in the current tool path
- 591 market/community pages
  - likely useful for market context and community discovery
  - may be more JS-heavy and require a more careful fetch path
- Sinyi tradeinfo / broader transaction pages
  - potentially useful as a transaction-oriented source after community-page ingestion is stable

## Recommended implementation order
1. add a `source_registry` mapping file for community -> second-source URL/id
2. create `scripts/fetch_latest_sinyi_community_data.py`
3. ingest raw rows into `observations.json` with explicit `source`, `source_url`, `raw_hash`
4. keep new rows separated from display until parsing quality is reviewed
5. only then decide which Sinyi-derived rows are eligible for public dashboard use

## Implementation principle: parameterized source scripts
To keep the project maintainable, source ingestion should be scriptable and parameterized:
- a fetch script should accept a target community as an argument when needed
- the same script should also support batch mode for all mapped communities
- adding a new community should usually mean only updating the mapping file, not rewriting parser logic
- parsing should prefer stable JSON/state blobs from the page over brittle free-text scraping when possible
