#!/usr/bin/env python3
import hashlib
import json
import re
import subprocess
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
OBS_PATH = ROOT / 'data' / 'observations.json'
CACHE_PATH = ROOT / 'data' / 'community_fetch_cache.json'

BASE_SEARCH = 'https://community.houseprice.tw/list/%E6%96%B0%E5%8C%97%E5%B8%82_city/%E6%B7%A1%E6%B0%B4%E5%8D%80_zip/{kw}_kw/'
BASE_BUILDING = 'https://community.houseprice.tw/building/{building_id}/'
UA = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36'
KNOWN_BUILDING_IDS = {
    '摩納哥社區': '174606',
    '水立方': '172908',
    '托斯卡尼翡冷翠': '7475',
    '托斯卡尼麥迪奇名家': '7479',
    '荷雅名人館': '8529',
    '荷雅時尚館': '174913',
    '尚海': '169930',
    '清淞': '174701',
    '高第': '21875',
}

LAYOUT_MAP = {
    '0': '套房',
    '1': '1房',
    '2': '2房',
    '3': '3房',
}


def http_get(url: str) -> str:
    res = subprocess.run(
        [
            'curl', '-L', '--silent', '--show-error',
            '-A', UA,
            '-H', 'Accept-Language: zh-TW,zh;q=0.9',
            url,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def watched_communities():
    watch = load_json(WATCHLIST_PATH, {})
    names = []
    for c in watch.get('communities', []):
        if isinstance(c, dict):
            if c.get('name'):
                names.append(c['name'])
            names.extend(c.get('nearby_communities', []))
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


def find_building_id(community: str, cache: dict):
    if community in KNOWN_BUILDING_IDS:
        building_id = KNOWN_BUILDING_IDS[community]
        cache[community] = {'building_id': building_id, 'resolved_at': str(date.today()), 'search_url': 'known-map'}
        return building_id
    if community in cache and cache[community].get('building_id'):
        return cache[community]['building_id']
    url = BASE_SEARCH.format(kw=quote(community))
    html = http_get(url)
    m = re.search(r'/building/(\d+)/', html)
    if not m:
        return None
    building_id = m.group(1)
    cache[community] = {'building_id': building_id, 'resolved_at': str(date.today()), 'search_url': url}
    return building_id


def normalize_month(roc_text: str) -> str:
    m = re.match(r'(\d{2,3})年(\d{2})月', roc_text)
    if not m:
        return ''
    roc_year = int(m.group(1))
    month = int(m.group(2))
    year = roc_year + 1911
    return f'{year:04d}-{month:02d}'


def month_to_date(month: str) -> str:
    return month + '-01' if month else str(date.today())


def parse_records(html: str, source_url: str, community: str):
    rows = []
    blocks = re.split(r'(?=(?:\d{2,3}年\d{2}月))', html)
    for block in blocks:
        mm = re.match(r'(\d{2,3}年\d{2}月)', block)
        if not mm:
            continue
        observed_month = normalize_month(mm.group(1))
        layout_m = re.search(r'\n\s*(大樓|華廈|公寓|套房|車位|店面|其他)\s*\n\s*(\d+)房\(室\)', block)
        if not layout_m:
            continue
        building_type = layout_m.group(1)
        rooms_num = layout_m.group(2)
        if building_type == '車位':
            continue
        total_m = re.search(r'\n\s*(\d+(?:\.\d+)?)\s*\n\s*萬\s*\n', block)
        unit_m = re.search(r'\n\s*(\d+(?:\.\d+)?)\s*\n\s*萬\s*\n(?:\s*已扣除車位\s*\n)?\s*(\d+(?:\.\d+)?)\s*\n\s*坪', block)
        age_m = re.search(r'\n\s*(\d+(?:\.\d+)?)\s*年\s*\n', block)
        parking = '含車位' in block or '坡道平面' in block or '升降機械' in block
        if not total_m or not unit_m:
            continue
        total_price = float(total_m.group(1))
        unit_price = float(unit_m.group(1))
        size_ping = float(unit_m.group(2))
        building_age = float(age_m.group(1)) if age_m else 0.0
        rooms = float(rooms_num)
        layout_type = LAYOUT_MAP.get(rooms_num, '4房以上' if rooms >= 4 else f'{rooms_num}房')
        address_m = re.search(rf'{re.escape(mm.group(1))}\s*\n\s*([^\n]+)', block)
        floor_m = re.search(r'\n\s*(\d+\s*/\d+|/\d+)\s*\n', block)
        address_text = address_m.group(1).strip() if address_m else ''
        floor_text = floor_m.group(1).replace(' ', '') if floor_m else ''
        base = {
            'observed_at': month_to_date(observed_month),
            'observed_month': observed_month,
            'type': 'listing',
            'region': '淡水',
            'community': community,
            'layout_type': layout_type,
            'rooms': rooms,
            'source': 'community.houseprice.tw',
            'source_type': 'listing',
            'source_url': source_url,
            'total_price': total_price,
            'unit_price': unit_price,
            'size_ping': size_ping,
            'building_age': building_age,
            'parking': bool(parking),
            'address_text': address_text,
            'floor_text': floor_text,
            'note': 'weekly auto-fetch from community page',
        }
        raw_key = '|'.join([
            base['observed_month'], base['community'], base['layout_type'],
            str(base['total_price']), str(base['unit_price']), str(base['size_ping']),
            address_text, floor_text
        ])
        base['raw_hash'] = hashlib.sha1(raw_key.encode('utf-8')).hexdigest()[:16]
        rows.append(base)
    return rows


def main():
    cache = load_json(CACHE_PATH, {})
    rows = load_json(OBS_PATH, [])
    existing = {r.get('raw_hash') for r in rows if r.get('raw_hash')}
    communities = watched_communities()
    added = []
    failures = []
    for community in communities:
        try:
            building_id = find_building_id(community, cache)
            if not building_id:
                failures.append({'community': community, 'error': 'building_id_not_found'})
                continue
            url = BASE_BUILDING.format(building_id=building_id)
            html = http_get(url)
            parsed = parse_records(html, url, community)
            new_rows = [r for r in parsed if r['raw_hash'] not in existing]
            for r in new_rows:
                existing.add(r['raw_hash'])
                rows.append(r)
            added.extend(new_rows)
            time.sleep(1.0)
        except Exception as e:
            failures.append({'community': community, 'error': str(e)})
    save_json(CACHE_PATH, cache)
    save_json(OBS_PATH, rows)
    summary = {
        'ok': True,
        'watched_communities': len(communities),
        'added_rows': len(added),
        'added_by_community': {c: sum(1 for r in added if r['community'] == c) for c in sorted({r['community'] for r in added})},
        'failures': failures,
        'total_rows': len(rows),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
