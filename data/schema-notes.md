# Schema Notes

## Current direction

This tracker is **not primarily a single-listing dedup database**.
It is now a **baseline-first monthly tracker**.
The main goal is to build a long-term price series for:

- each `community`
- each `layout_type`
- across time (`observed_month`)

So the recommended mental model is:

1. Keep raw observations / usable anchors
2. Rebuild a monthly baseline layer for analysis
3. Use filtering/views later instead of prematurely throwing data away

## Observation fields

- `observed_at`: raw observation date (`YYYY-MM-DD` preferred)
- `observed_month`: derived month bucket (`YYYY-MM`)
- `type`: `listing` / `seed` / other future event types
- `region`
- `community`
- `layout_type`
- `rooms`
- `source`
- `source_type`: e.g. `listing`, `baseline` (current primary layer is `baseline`)
- `source_url`: optional original page URL
- `address_text`: optional source address text
- `floor_text`: optional floor text
- `total_price`
- `unit_price`
- `size_ping`
- `building_age`
- `parking`
- `note`
- `raw_hash`: import-level fingerprint to avoid importing the exact same raw observation twice

## Dedup rule

Do **not** use `total_price` / `unit_price` as identity keys for properties over time.
Prices are expected to change.

Instead:
- use `raw_hash` only to block exact duplicate imports
- keep multiple observations for the same community/layout across time
- aggregate at `community + layout_type + observed_month`

## Analysis target

Main analysis should use monthly grouped metrics like:

- sample count
- average unit price
- median unit price
- min/max unit price
- average total price

These monthly grouped series are the real product.
