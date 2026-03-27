#!/usr/bin/env python3
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'

DEFAULT_START_MONTH = '2023-01'
DEFAULT_END_MONTH = '2026-03'
DEFAULT_LAYOUTS = ['1房', '2房', '3房', '4房以上']
BASELINE_SOURCE = 'public-baseline'
BASELINE_NOTE = 'baseline-first 月序列基準點（依現有可用公開資訊與既有樣本整理，用於長期追蹤每月價位）'
DEFAULT_REGION = '淡水'


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def avg(values):
    vals = [float(v) for v in values if isinstance(v, (int, float)) and v > 0]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def month_range(start, end):
    sy, sm = map(int, start.split('-'))
    ey, em = map(int, end.split('-'))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def month_to_date(month):
    return f'{month}-01'


def normalize_layouts(watchlist):
    layouts = [x for x in watchlist.get('layout_types', []) if x != '套房']
    return layouts or list(DEFAULT_LAYOUTS)


def collect_target_communities(watchlist):
    communities = []
    for item in watchlist.get('communities', []):
        name = item.get('name')
        if name:
            communities.append(name)
        communities.extend(item.get('nearby_communities', []))
    return list(dict.fromkeys(communities))


def parse_rooms(layout):
    if layout == '4房以上':
        return 4.0
    if layout.endswith('房'):
        try:
            return float(layout.replace('房', ''))
        except ValueError:
            return 0.0
    return 0.0


def baseline_hash(community, layout, month):
    key = f'baseline|{community}|{layout}|{month}'
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def is_usable_anchor(row):
    return bool(row.get('community')) and bool(row.get('unit_price', 0))


def build_anchor_map(rows):
    anchors = defaultdict(list)
    for row in rows:
        if not is_usable_anchor(row):
            continue
        community = row.get('community')
        layout = row.get('layout_type') or '未分類'
        anchors[(community, layout)].append({
            'unit_price': row.get('unit_price', 0),
            'total_price': row.get('total_price', 0),
            'size_ping': row.get('size_ping', 0),
            'building_age': row.get('building_age', 0),
        })
    return anchors


def strip_existing_baselines(rows):
    return [row for row in rows if row.get('source') != BASELINE_SOURCE]


def summarize_anchor_samples(samples):
    return {
        'unit_price': avg([x['unit_price'] for x in samples]),
        'total_price': avg([x['total_price'] for x in samples]),
        'size_ping': avg([x['size_ping'] for x in samples]),
        'building_age': avg([x['building_age'] for x in samples]),
    }


def collect_community_layout_map(anchors):
    by_community = defaultdict(dict)
    for (community, layout), samples in anchors.items():
        by_community[community][layout] = summarize_anchor_samples(samples)
    return by_community


def fallback_anchor_summary(community, layout, community_layout_map, global_layout_map):
    if layout in community_layout_map.get(community, {}):
        return community_layout_map[community][layout], 'direct-layout-anchor'

    same_community = list(community_layout_map.get(community, {}).values())
    if same_community:
        return summarize_anchor_samples(same_community), 'same-community-fallback'

    layout_global = global_layout_map.get(layout, [])
    if layout_global:
        return summarize_anchor_samples(layout_global), 'same-layout-global-fallback'

    all_global = []
    for samples in global_layout_map.values():
        all_global.extend(samples)
    if all_global:
        return summarize_anchor_samples(all_global), 'global-fallback'

    return None, 'missing-anchor'


def make_baseline_row(community, layout, month, anchor_summary, anchor_mode):
    return {
        'observed_at': month_to_date(month),
        'observed_month': month,
        'type': 'seed',
        'region': DEFAULT_REGION,
        'community': community,
        'layout_type': layout,
        'rooms': parse_rooms(layout),
        'source': BASELINE_SOURCE,
        'source_type': 'baseline',
        'source_url': '',
        'total_price': anchor_summary['total_price'],
        'unit_price': anchor_summary['unit_price'],
        'size_ping': anchor_summary['size_ping'],
        'building_age': anchor_summary['building_age'],
        'parking': False,
        'address_text': '',
        'floor_text': '',
        'note': f'{BASELINE_NOTE}；anchor={anchor_mode}',
        'raw_hash': baseline_hash(community, layout, month),
    }


def build_global_layout_map(anchors):
    global_layout_map = defaultdict(list)
    for (_, layout), samples in anchors.items():
        global_layout_map[layout].extend(samples)
    return global_layout_map


def build_baseline_rows(communities, layouts, months, anchors):
    new_rows = []
    community_layout_map = collect_community_layout_map(anchors)
    global_layout_map = build_global_layout_map(anchors)
    for community in communities:
        for layout in layouts:
            anchor_summary, anchor_mode = fallback_anchor_summary(community, layout, community_layout_map, global_layout_map)
            if not anchor_summary:
                continue
            for month in months:
                new_rows.append(make_baseline_row(community, layout, month, anchor_summary, anchor_mode))
    return new_rows


def sort_rows(rows):
    rows.sort(key=lambda row: (
        row.get('observed_at', ''),
        row.get('community', ''),
        row.get('layout_type', ''),
        row.get('raw_hash', ''),
    ))
    return rows


def main():
    rows = load_json(DATA_PATH, [])
    watchlist = load_json(WATCHLIST_PATH, {'communities': [], 'layout_types': []})

    layouts = normalize_layouts(watchlist)
    communities = collect_target_communities(watchlist)
    months = month_range(DEFAULT_START_MONTH, DEFAULT_END_MONTH)

    kept_rows = strip_existing_baselines(rows)
    anchors = build_anchor_map(kept_rows)
    baseline_rows = build_baseline_rows(communities, layouts, months, anchors)

    merged_rows = sort_rows(kept_rows + baseline_rows)
    save_json(DATA_PATH, merged_rows)

    print(json.dumps({
        'ok': True,
        'kept_rows': len(kept_rows),
        'baseline_rows': len(baseline_rows),
        'total_rows': len(merged_rows),
        'communities': communities,
        'layouts': layouts,
        'months': len(months),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
