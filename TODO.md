# TODO

## Immediate
- [x] Ingest initial Sinyi community data for the 4 validated mapped communities.
- [x] Rebuild dashboard after the initial Sinyi ingest so website reflects the new rows.
- [ ] Integrate `data/coverage_refresh_state.json` generation into the weekly fetch pipeline.
- [ ] Make the weekly pipeline report which community/layout combinations were updated, unchanged, or still missing.

## Sinyi second-source expansion
- [x] Use `__NEXT_DATA__` JSON as the preferred parser input instead of brittle free-text scraping.
- [x] Support parameterized fetch mode (`--community`) and batch mode (`--all-mapped`).
- [ ] Validate the currently ingested 20 Sinyi rows against dashboard visibility and display logic.
- [ ] Add/verify Sinyi mappings for the remaining watched communities without reliable source coverage.
- [ ] Decide per-source normalization rules for layout parsing so `未分類` rows are reduced.

## Data coverage / refresh tracking
- [x] Create `data/coverage_refresh_state.json`.
- [ ] Update refresh state automatically after every fetch/rebuild run.
- [ ] Add a quick audit script/view for stale community × layout pairs.
- [ ] Use refresh state to avoid duplicate work and identify communities that still need source mapping.

## Website / deployment
- [x] Rebuild the site after local data changes.
- [ ] Push each material update to remote after verifying generated files changed as expected.
- [ ] Confirm newly added Sinyi-backed rows are visible in the published dashboard and note where they appear.

## Remaining no-data communities
- [ ] Continue filling remaining watched communities that still lack usable displayable data.
- [ ] Prefer source-backed additions only; do not reintroduce fallback-derived fake coverage.
- [ ] Track unresolved communities explicitly rather than silently omitting them.
