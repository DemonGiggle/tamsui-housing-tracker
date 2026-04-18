#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
MAP_PATH = ROOT / 'data' / 'leju_community_map.json'
CACHE_PATH = ROOT / 'data' / 'leju_fetch_cache.json'
UA = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36'


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


def brave_search(query: str):
    cmd = ['openclaw', 'tool', 'web_search', json.dumps({'query': query, 'count': 5, 'country': 'TW', 'language': 'zh'})]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or 'web_search_failed').strip())
    return json.loads(res.stdout)


def extract_leju_result(search_json):
    results = search_json.get('results') or []
    for item in results:
        url = item.get('url') or ''
        title = item.get('title') or ''
        desc = item.get('description') or ''
        if 'www.leju.com.tw/community/' not in url:
            continue
        m = re.search(r'/community/([A-Za-z0-9]+)', url)
        if not m:
            continue
        name = ''
        mt = re.search(r'【([^】]+)】', title)
        if mt:
            name = mt.group(1)
        return {
            'community_name': name,
            'oid': m.group(1),
            'url': url,
            'snippet': desc,
        }
    return None


def resolve_targets(args, mapping):
    if args.community:
        return [args.community]
    if args.all_mapped:
        return list(mapping.keys())
    return watched_communities()


def main():
    parser = argparse.ArgumentParser(description='Bootstrap Leju community URLs via search results')
    parser.add_argument('--community', help='resolve one community')
    parser.add_argument('--all-mapped', action='store_true', help='refresh all already mapped communities')
    parser.add_argument('--dry-run', action='store_true', help='do not write files')
    args = parser.parse_args()

    mapping = load_json(MAP_PATH, {})
    cache = load_json(CACHE_PATH, {})
    targets = resolve_targets(args, mapping)

    updated = {}
    failures = []
    skipped = []

    for community in targets:
        if community in mapping and not args.all_mapped and not args.community:
            skipped.append({'community': community, 'reason': 'already_mapped'})
            continue
        query = f'site:leju.com.tw {community} 淡水 樂居'
        try:
            result = brave_search(query)
            found = extract_leju_result(result)
            if not found:
                failures.append({'community': community, 'error': 'community_page_not_found'})
                cache[community] = {
                    'last_fetch': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                    'query': query,
                    'status': 'not_found',
                }
                continue
            updated[community] = {
                'community_name': found['community_name'] or community,
                'oid': found['oid'],
                'url': found['url'],
                'source': 'search-bootstrap',
            }
            cache[community] = {
                'last_fetch': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                'query': query,
                'status': 'ok',
                'oid': found['oid'],
                'url': found['url'],
            }
            time.sleep(0.5)
        except Exception as e:
            failures.append({'community': community, 'error': str(e)})
            cache[community] = {
                'last_fetch': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                'query': query,
                'status': 'error',
                'error': str(e),
            }

    merged = dict(mapping)
    merged.update(updated)

    if not args.dry_run:
        save_json(MAP_PATH, merged)
        save_json(CACHE_PATH, cache)

    summary = {
        'ok': True,
        'targets': targets,
        'updated': sorted(updated.keys()),
        'updated_count': len(updated),
        'skipped': skipped,
        'failures': failures,
        'dry_run': args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
