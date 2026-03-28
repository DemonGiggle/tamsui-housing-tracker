#!/usr/bin/env python3
import hashlib
import json
import re
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
OBS_PATH = ROOT / 'data' / 'observations.json'
MAP_PATH = ROOT / 'data' / 'sinyi_community_map.json'
CACHE_PATH = ROOT / 'data' / 'sinyi_fetch_cache.json'
UA = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36'

ROOM_PAT = re.compile(r'(?P<rooms>\d+)房')
MONTH_PAT = re.compile(r'(?P<roc>\d{2,3}年\d{2}月)')
PRICE_PAT = re.compile(r'(?P<price>\d+(?:,\d{3})*(?:\.\d+)?)萬')
UNIT_PAT = re.compile(r'(?P<unit>\d+(?:\.\d+)?)萬/坪')
SIZE_PAT = re.compile(r'建坪(?P<size>\d+(?:\.\d+)?)坪')
AGE_PAT = re.compile(r'(?P<age>\d+(?:\.\d+)?)年')
FLOOR_PAT = re.compile(r'(?P<floor>\d+樓/\d+樓)')
ADDRESS_PAT = re.compile(r'新北市淡水區[^\s]+')
COMMUNITY_PAT = re.compile(r'^(?P<name>.+?)實價登錄', re.M)


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
            if c.get('name') and c['name'] not in names:
                names.append(c['name'])
            for nearby in c.get('nearby_communities', []):
                if nearby not in names:
                    names.append(nearby)
    return names


def normalize_month(roc_text: str) -> str:
    m = re.match(r'(\d{2,3})年(\d{2})月', roc_text)
    if not m:
        return ''
    return f'{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}'


def month_to_date(month: str) -> str:
    return month + '-01' if month else str(date.today())


def infer_layout_type(text: str) -> str:
    m = ROOM_PAT.search(text)
    if not m:
        return '未分類'
    rooms = int(m.group('rooms'))
    if rooms == 0:
        return '套房'
    if rooms >= 4:
        return '4房以上'
    return f'{rooms}房'


def extract_first(pattern, text, cast=str, default=None):
    m = pattern.search(text)
    if not m:
        return default
    if m.groupdict():
        value = next((v for v in m.groupdict().values() if v is not None), None)
    else:
        value = m.group(0)
    if value is None:
        return default
    if cast is str:
        return value
    return cast(value.replace(',', '')) if cast else value


def parse_rows(text: str, source_url: str, watch_community: str):
    rows = []
    blocks = re.split(r'(?=(?:\d{2,3}年\d{2}月))', text)
    for block in blocks:
        month_match = MONTH_PAT.match(block.strip())
        if not month_match:
            continue
        observed_month = normalize_month(month_match.group('roc'))
        unit_price = extract_first(UNIT_PAT, block, float)
        total_price = extract_first(PRICE_PAT, block, float)
        size_ping = extract_first(SIZE_PAT, block, float, 0.0)
        building_age = extract_first(AGE_PAT, block, float, 0.0)
        address_text = extract_first(ADDRESS_PAT, block, str, '') or ''
        floor_text = extract_first(FLOOR_PAT, block, str, '') or ''
        layout_type = infer_layout_type(block)
        rooms_match = ROOM_PAT.search(block)
        rooms = float(rooms_match.group('rooms')) if rooms_match else 0.0
        parking = '有車位' in block or '含車位' in block
        if not observed_month or not unit_price or not total_price:
            continue
        raw_key = '|'.join([
            'sinyi-community',
            watch_community,
            observed_month,
            layout_type,
            str(total_price),
            str(unit_price),
            str(size_ping),
            address_text,
            floor_text,
        ])
        rows.append({
            'observed_at': month_to_date(observed_month),
            'observed_month': observed_month,
            'type': 'listing',
            'region': '淡水',
            'community': watch_community,
            'layout_type': layout_type,
            'rooms': rooms,
            'source': 'sinyi.community',
            'source_type': 'listing',
            'source_url': source_url,
            'total_price': total_price,
            'unit_price': unit_price,
            'size_ping': size_ping,
            'building_age': building_age,
            'parking': parking,
            'address_text': address_text,
            'floor_text': floor_text,
            'note': 'weekly auto-fetch from Sinyi community page',
            'fetched_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            'raw_hash': hashlib.sha1(raw_key.encode('utf-8')).hexdigest()[:16],
        })
    return rows


def main():
    mapping = load_json(MAP_PATH, {})
    cache = load_json(CACHE_PATH, {})
    rows = load_json(OBS_PATH, [])
    existing = {r.get('raw_hash') for r in rows if r.get('raw_hash')}

    added = []
    failures = []
    skipped = []

    for community in watched_communities():
        info = mapping.get(community)
        if not info:
            skipped.append({'community': community, 'reason': 'mapping_missing'})
            continue
        url = info['url']
        try:
            text = http_get(url)
            parsed = parse_rows(text, url, community)
            new_rows = [r for r in parsed if r['raw_hash'] not in existing]
            for row in new_rows:
                existing.add(row['raw_hash'])
                rows.append(row)
            added.extend(new_rows)
            cache[community] = {
                'url': url,
                'last_fetch': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
                'parsed_rows': len(parsed),
                'new_rows': len(new_rows),
            }
            time.sleep(1.0)
        except Exception as e:
            failures.append({'community': community, 'error': repr(e)})

    save_json(CACHE_PATH, cache)
    save_json(OBS_PATH, rows)

    summary = {
        'ok': True,
        'mapped_communities': len(mapping),
        'watched_communities': len(watched_communities()),
        'added_rows': len(added),
        'added_by_community': {c: sum(1 for r in added if r['community'] == c) for c in sorted({r['community'] for r in added})},
        'skipped': skipped,
        'failures': failures,
        'total_rows': len(rows),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
