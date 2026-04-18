#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
OBS_PATH = ROOT / 'data' / 'observations.json'
MAP_PATH = ROOT / 'data' / 'sinyi_community_map.json'
CACHE_PATH = ROOT / 'data' / 'sinyi_fetch_cache.json'
UA = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36'
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def merge_rows_by_hash(existing_rows, new_rows):
    merged = []
    seen = set()
    for row in existing_rows + new_rows:
        raw_hash = row.get('raw_hash')
        key = raw_hash or json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    merged.sort(key=lambda row: (
        row.get('observed_at', ''),
        row.get('community', ''),
        row.get('layout_type', ''),
        row.get('raw_hash', ''),
    ))
    return merged


def http_get(url: str) -> str:
    res = subprocess.run(
        [
            'curl', '-L', '--silent', '--show-error', '--fail',
            '-A', UA,
            '-H', 'Accept-Language: zh-TW,zh;q=0.9',
            url,
        ],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        detail = (res.stderr or res.stdout or f'curl_exit_{res.returncode}').strip()
        raise RuntimeError(detail)
    return res.stdout


def watched_communities():
    watch = load_json(WATCHLIST_PATH, {})
    names = []
    for c in watch.get('communities', []):
        if isinstance(c, dict):
            if c.get('name') and c['name'] not in names:
                names.append(c['name'])
            for nearby in c.get('nearby_communities', []):
                if nearby not in names:
                    names.append(nearby)
    return names


def extract_next_data(html: str):
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise RuntimeError('next_data_not_found')
    return json.loads(m.group(1))


def roc_to_iso_month(value):
    if value is None:
        return ''
    text = str(value)
    m = re.match(r'^(\d{2,3})(\d{2})$', text)
    if m:
        year = int(m.group(1)) + 1911
        month = int(m.group(2))
        return f'{year:04d}-{month:02d}'
    m = re.match(r'^(\d{4})(\d{2})$', text)
    if m:
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}'
    return ''


def infer_layout_type(item):
    rooms = item.get('room')
    if isinstance(rooms, (int, float)):
        if rooms == 0:
            return '套房'
        if rooms >= 4:
            return '4房以上'
        return f'{int(rooms)}房'
    kind = str(item.get('pattern') or item.get('layout') or item.get('type') or '')
    m = re.search(r'(\d+)房', kind)
    if m:
        n = int(m.group(1))
        if n >= 4:
            return '4房以上'
        return f'{n}房'
    if '套房' in kind:
        return '套房'
    return '未分類'


def to_float(v, default=0.0):
    if v in (None, ''):
        return default
    try:
        return float(v)
    except Exception:
        return default


def to_bool_parking(item):
    if item.get('parkingprice') not in (None, '', 0):
        return True
    if item.get('refparkingprice') not in (None, '', 0):
        return True
    text = ' '.join(str(item.get(k) or '') for k in ['car', 'memo', 'note', 'type'])
    return '車位' in text


def normalize_trade_row(item, watch_community, source_url):
    observed_month = roc_to_iso_month(item.get('soldDate'))
    if not observed_month:
        return None
    total_price = to_float(item.get('totalPrice'))
    unit_price = to_float(item.get('uniPrice'))
    ref_unit_price = to_float(item.get('refuniprice'))
    size_ping = to_float(item.get('areaBuilding'))
    building_age = to_float(item.get('houseAge'))
    rooms = to_float(item.get('room'))
    address_text = str(item.get('address') or '')
    floor_text = str(item.get('floor') or '')
    layout_type = infer_layout_type(item)
    if total_price <= 0 or unit_price <= 0:
        return None
    raw_key = '|'.join([
        'sinyi.community',
        str(item.get('tradeID') or ''),
        watch_community,
        observed_month,
        str(total_price),
        str(unit_price),
        address_text,
    ])
    return {
        'observed_at': observed_month + '-01',
        'observed_month': observed_month,
        'type': 'listing',
        'region': '淡水',
        'community': watch_community,
        'layout_type': layout_type,
        'rooms': rooms,
        'source': 'sinyi.community',
        'source_type': 'listing',
        'source_url': source_url,
        'source_record_id': str(item.get('tradeID') or ''),
        'total_price': total_price,
        'unit_price': unit_price,
        'ref_unit_price': ref_unit_price,
        'size_ping': size_ping,
        'building_age': building_age,
        'parking': to_bool_parking(item),
        'address_text': address_text,
        'floor_text': floor_text,
        'note': 'weekly auto-fetch from Sinyi __NEXT_DATA__ tradeData',
        'fetched_at': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'raw_hash': hashlib.sha1(raw_key.encode('utf-8')).hexdigest()[:16],
    }


def parse_page(html: str, watch_community: str, source_url: str):
    data = extract_next_data(html)
    reducer = data['props']['initialReduxState']['communityReducer']
    trade_data = reducer.get('tradeData') or []
    community_trend = ((reducer.get('communityTrendList') or {}).get('communityTrend')) or []

    rows = []
    for item in trade_data:
        row = normalize_trade_row(item, watch_community, source_url)
        if row:
            rows.append(row)

    trend_points = []
    for item in community_trend:
        month = roc_to_iso_month(item.get('date'))
        uni = to_float(item.get('uniPrice'))
        if month and uni > 0:
            trend_points.append({
                'month': month,
                'uni_price': uni,
                'trans_count': item.get('transCount'),
            })

    meta = reducer.get('communityContentList') or {}
    return {
        'rows': rows,
        'trend_points': trend_points,
        'meta': {
            'source_name': meta.get('name'),
            'address': meta.get('address'),
            'age': meta.get('age'),
            'households': meta.get('holdnum') or meta.get('houseNum'),
        }
    }


def resolve_targets(args, mapping):
    if args.community:
        return [args.community]
    if args.all_mapped:
        return list(mapping.keys())
    targets = []
    for name in watched_communities():
        if name in mapping:
            targets.append(name)
    return targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--community', help='fetch only one mapped watchlist community name')
    parser.add_argument('--all-mapped', action='store_true', help='fetch all mapped communities')
    parser.add_argument('--dry-run', action='store_true', help='do not write observations.json')
    args = parser.parse_args()

    mapping = load_json(MAP_PATH, {})
    cache = load_json(CACHE_PATH, {})
    rows = load_json(OBS_PATH, [])
    existing = {r.get('raw_hash') for r in rows if r.get('raw_hash')}

    targets = resolve_targets(args, mapping)
    added = []
    failures = []
    skipped = []

    for community in targets:
        info = mapping.get(community)
        if not info:
            skipped.append({'community': community, 'reason': 'mapping_missing'})
            continue
        url = info['url']
        try:
            html = http_get(url)
            parsed = parse_page(html, community, url)
            new_rows = [r for r in parsed['rows'] if r['raw_hash'] not in existing]
            if not args.dry_run:
                for row in new_rows:
                    existing.add(row['raw_hash'])
                    rows.append(row)
            added.extend(new_rows)
            cache[community] = {
                'url': url,
                'last_fetch': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                'html_size': len(html),
                'source_name': parsed['meta'].get('source_name'),
                'parsed_rows': len(parsed['rows']),
                'new_rows': len(new_rows),
                'trend_points': len(parsed['trend_points']),
                'parser_status': 'ok',
            }
            time.sleep(1.0)
        except Exception as e:
            failures.append({'community': community, 'error': repr(e)})
            cache[community] = {
                'url': url,
                'last_fetch': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                'parser_status': 'error',
                'error': repr(e),
            }

    save_json(CACHE_PATH, cache)
    if not args.dry_run:
        latest_rows = load_json(OBS_PATH, [])
        merged_rows = merge_rows_by_hash(latest_rows, rows)
        save_json(OBS_PATH, merged_rows)
        rows = merged_rows

    summary = {
        'ok': True,
        'targets': targets,
        'mapped_communities': len(mapping),
        'added_rows': len(added),
        'added_by_community': {c: sum(1 for r in added if r['community'] == c) for c in sorted({r['community'] for r in added})},
        'skipped': skipped,
        'failures': failures,
        'total_rows': len(rows) if not args.dry_run else len(load_json(OBS_PATH, [])),
        'dry_run': args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
