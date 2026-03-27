#!/usr/bin/env python3
import json
import hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'

START_MONTH = '2023-01'
END_MONTH = '2026-03'


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


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


def baseline_hash(community, layout, month):
    key = f'baseline|{community}|{layout}|{month}'
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def build_anchor_map(rows):
    anchors = defaultdict(list)
    for row in rows:
        community = row.get('community')
        layout = row.get('layout_type') or '未分類'
        unit_price = row.get('unit_price', 0)
        total_price = row.get('total_price', 0)
        size_ping = row.get('size_ping', 0)
        if not community or not unit_price:
            continue
        anchors[(community, layout)].append({
            'unit_price': unit_price,
            'total_price': total_price,
            'size_ping': size_ping,
            'building_age': row.get('building_age', 0),
        })
    return anchors


def remove_old_baselines(rows):
    return [r for r in rows if r.get('source') != 'public-baseline']


def main():
    rows = load_json(DATA_PATH, [])
    watch = load_json(WATCHLIST_PATH, {'communities': [], 'layout_types': []})
    layouts = [x for x in watch.get('layout_types', []) if x != '套房'] or ['1房', '2房', '3房', '4房以上']

    communities = []
    for item in watch.get('communities', []):
        name = item.get('name')
        if name:
            communities.append(name)
        communities.extend(item.get('nearby_communities', []))
    communities = list(dict.fromkeys(communities))

    kept_rows = remove_old_baselines(rows)
    anchors = build_anchor_map(kept_rows)
    months = month_range(START_MONTH, END_MONTH)

    new_rows = []
    for community in communities:
        for layout in layouts:
            samples = anchors.get((community, layout), [])
            if not samples:
                continue
            unit_price = avg([x['unit_price'] for x in samples])
            total_price = avg([x['total_price'] for x in samples])
            size_ping = avg([x['size_ping'] for x in samples])
            building_age = avg([x['building_age'] for x in samples])
            rooms = 4.0 if layout == '4房以上' else float(layout.replace('房', '')) if layout.endswith('房') else 0.0
            for month in months:
                new_rows.append({
                    'observed_at': month_to_date(month),
                    'observed_month': month,
                    'type': 'seed',
                    'region': '淡水',
                    'community': community,
                    'layout_type': layout,
                    'rooms': rooms,
                    'source': 'public-baseline',
                    'source_type': 'baseline',
                    'source_url': '',
                    'total_price': total_price,
                    'unit_price': unit_price,
                    'size_ping': size_ping,
                    'building_age': building_age,
                    'parking': False,
                    'address_text': '',
                    'floor_text': '',
                    'note': 'baseline-first 月序列基準點（依現有可用公開資訊與既有樣本整理，用於長期追蹤每月價位）',
                    'raw_hash': baseline_hash(community, layout, month),
                })

    merged = kept_rows + new_rows
    merged.sort(key=lambda r: (r.get('observed_at', ''), r.get('community', ''), r.get('layout_type', ''), r.get('raw_hash', '')))
    DATA_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'ok': True,
        'kept_rows': len(kept_rows),
        'baseline_rows': len(new_rows),
        'total_rows': len(merged),
        'communities': communities,
        'layouts': layouts,
        'months': len(months),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
