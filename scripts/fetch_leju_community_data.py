#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
MAP_PATH = ROOT / 'data' / 'leju_community_map.json'
CACHE_PATH = ROOT / 'data' / 'leju_fetch_cache.json'


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


def resolve_targets(args, mapping):
    if args.community:
        return [args.community]
    if args.all_mapped:
        return list(mapping.keys())
    return [name for name in watched_communities() if name in mapping]


def main():
    parser = argparse.ArgumentParser(description='Leju community mapping/status helper')
    parser.add_argument('--community', help='check one mapped community')
    parser.add_argument('--all-mapped', action='store_true', help='check all mapped communities')
    parser.add_argument('--dry-run', action='store_true', help='do not write cache file')
    args = parser.parse_args()

    mapping = load_json(MAP_PATH, {})
    cache = load_json(CACHE_PATH, {})
    targets = resolve_targets(args, mapping)

    checked = []
    missing = []
    now = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    for community in targets:
        info = mapping.get(community)
        if not info:
            missing.append(community)
            continue
        checked.append({
            'community': community,
            'oid': info.get('oid'),
            'url': info.get('url'),
            'status': 'mapped',
            'fetch_mode': 'browser-session-required',
        })
        cache[community] = {
            'last_checked': now,
            'status': 'mapped',
            'fetch_mode': 'browser-session-required',
            'oid': info.get('oid'),
            'url': info.get('url'),
            'note': 'Leju is currently protected by Cloudflare bot checks. Use browser-assisted extraction after verification passes in a real browser session.',
        }

    if not args.dry_run:
        save_json(CACHE_PATH, cache)

    summary = {
        'ok': True,
        'targets': targets,
        'checked': checked,
        'missing': missing,
        'checked_count': len(checked),
        'dry_run': args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
