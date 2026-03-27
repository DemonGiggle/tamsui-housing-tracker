#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import ssl
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'

DEFAULT_COMMUNITIES = [
    '摩納哥社區', '水立方', '托斯卡尼翡冷翠', '托斯卡尼麥迪奇名家',
    '荷雅名人館', '荷雅時尚館', '尚海', '清淞', '高第'
]
DEFAULT_LAYOUTS = ['1房', '2房', '3房', '4房以上']
UA = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'


@dataclass
class Observation:
    observed_at: str
    community: str
    layout_type: str
    rooms: float
    total_price: float
    unit_price: float
    size_ping: float
    building_age: float
    source: str
    source_type: str
    source_url: str
    address_text: str = ''
    floor_text: str = ''
    note: str = ''
    parking: bool = False

    def to_row(self):
        raw_key = '|'.join([
            self.community,
            self.layout_type,
            self.observed_at,
            f'{self.total_price}',
            f'{self.unit_price}',
            f'{self.size_ping}',
            self.source,
            self.source_url,
            self.address_text,
            self.floor_text,
        ])
        raw_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:16]
        return {
            'observed_at': self.observed_at,
            'observed_month': self.observed_at[:7],
            'type': 'listing',
            'region': '淡水',
            'community': self.community,
            'layout_type': self.layout_type,
            'rooms': self.rooms,
            'source': self.source,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'total_price': self.total_price,
            'unit_price': self.unit_price,
            'size_ping': self.size_ping,
            'building_age': self.building_age,
            'parking': self.parking,
            'address_text': self.address_text,
            'floor_text': self.floor_text,
            'note': self.note,
            'raw_hash': raw_hash,
        }


def load_rows():
    return json.loads(DATA_PATH.read_text()) if DATA_PATH.exists() else []


def save_rows(rows):
    rows.sort(key=lambda r: (r.get('observed_at', ''), r.get('community', ''), r.get('layout_type', ''), r.get('raw_hash', '')))
    DATA_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


def read_watchlist_communities():
    if not WATCHLIST_PATH.exists():
        return DEFAULT_COMMUNITIES
    data = json.loads(WATCHLIST_PATH.read_text())
    out = []
    for item in data.get('focal_communities', []):
        name = item.get('community') or item.get('name')
        if name:
            out.append(name)
        out.extend(item.get('nearby_communities', []))
    return out or DEFAULT_COMMUNITIES


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception:
        cmd = ['curl', '-L', '--max-time', '20', '-A', UA, '-k', url]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        return ''


def normalize_ws(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def parse_buy_houseprice_snippets(html: str, community: str) -> list[Observation]:
    # Conservative parser: only consumes snippets that clearly contain坪數/房/萬/單價/樓層/year-like text.
    text = normalize_ws(re.sub(r'<[^>]+>', ' ', html))
    chunks = re.split(r'(?=建物\s*\d+\.?\d*\s*坪)', text)
    found: list[Observation] = []
    for chunk in chunks:
        if '房' not in chunk or '萬' not in chunk or '坪' not in chunk:
            continue
        m_size = re.search(r'建物\s*(\d+(?:\.\d+)?)\s*坪', chunk)
        m_room = re.search(r'(\d+)\s*房', chunk)
        m_price = re.search(r'--\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*萬', chunk)
        m_unit = re.search(r'單價\s*(\d+(?:\.\d+)?)\s*萬', chunk)
        m_age = re.search(r'(\d+(?:\.\d+)?)\s*年', chunk)
        m_floor = re.search(r'(\d+(?:-\d+)?/\d+樓?)', chunk)
        m_addr = re.search(r'淡水區([^\s]{1,20})', chunk)
        if not (m_size and m_room and m_price and m_unit):
            continue
        rooms = float(m_room.group(1))
        layout = '4房以上' if rooms >= 4 else f'{int(rooms)}房'
        addr = ('淡水區' + m_addr.group(1)) if m_addr else '淡水區'
        found.append(Observation(
            observed_at='2026-03-27',
            community=community,
            layout_type=layout,
            rooms=rooms,
            total_price=float(m_price.group(1).replace(',', '')),
            unit_price=float(m_unit.group(1)),
            size_ping=float(m_size.group(1)),
            building_age=float(m_age.group(1)) if m_age else 0.0,
            source='buy.houseprice.tw',
            source_type='listing',
            source_url='',
            address_text=addr,
            floor_text=m_floor.group(1) if m_floor else '',
            note='待售頁面可驗證樣本（後續可再以成交頁補強）',
        ))
    return found


def import_from_search_pages(communities: Iterable[str], layouts: set[str]):
    imported: list[Observation] = []
    for community in communities:
        encoded = urllib.parse.quote(community)
        urls = [
            f'https://buy.houseprice.tw/list/%E6%96%B0%E5%8C%97%E5%B8%82_city/%E6%B7%A1%E6%B0%B4%E5%8D%80_zip/{encoded}_kw/',
        ]
        for url in urls:
            html = fetch_url(url)
            if not html or len(html) < 200:
                continue
            for obs in parse_buy_houseprice_snippets(html, community):
                if obs.layout_type in layouts:
                    obs.source_url = url
                    imported.append(obs)
    return imported


def merge_rows(existing_rows, observations: list[Observation]):
    seen = {r.get('raw_hash') for r in existing_rows}
    added = 0
    for obs in observations:
        row = obs.to_row()
        if row['raw_hash'] in seen:
            continue
        existing_rows.append(row)
        seen.add(row['raw_hash'])
        added += 1
    return added


def main():
    p = argparse.ArgumentParser(description='Import real samples from public housing sources')
    p.add_argument('--community', action='append', default=[])
    p.add_argument('--layout', action='append', default=[])
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    communities = args.community or read_watchlist_communities()
    layouts = set(args.layout or DEFAULT_LAYOUTS)

    rows = load_rows()
    observations: list[Observation] = []
    observations.extend(import_from_search_pages(communities, layouts))

    if args.dry_run:
        print(json.dumps({
            'communities': communities,
            'layouts': sorted(layouts),
            'candidate_count': len(observations),
            'sample': [o.to_row() for o in observations[:5]],
        }, ensure_ascii=False, indent=2))
        return

    added = merge_rows(rows, observations)
    save_rows(rows)
    print(json.dumps({
        'ok': True,
        'communities': communities,
        'layouts': sorted(layouts),
        'candidate_count': len(observations),
        'added': added,
        'total_rows': len(rows),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
