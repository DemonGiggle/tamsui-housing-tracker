#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'


def load_rows():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text())


def main():
    p = argparse.ArgumentParser(description='Append one housing observation')
    p.add_argument('--observed-at', default='')
    p.add_argument('--type', default='listing')
    p.add_argument('--region', required=True)
    p.add_argument('--community', default='')
    p.add_argument('--source', default='manual')
    p.add_argument('--total-price', type=float, default=0.0)
    p.add_argument('--unit-price', type=float, default=0.0)
    p.add_argument('--size-ping', type=float, default=0.0)
    p.add_argument('--building-age', type=float, default=0.0)
    p.add_argument('--parking', action='store_true')
    p.add_argument('--note', default='')
    args = p.parse_args()

    rows = load_rows()
    row = {
        'observed_at': args.observed_at or '2026-03-27',
        'type': args.type,
        'region': args.region,
        'community': args.community,
        'source': args.source,
        'total_price': args.total_price,
        'unit_price': args.unit_price,
        'size_ping': args.size_ping,
        'building_age': args.building_age,
        'parking': bool(args.parking),
        'note': args.note,
    }
    rows.append(row)
    DATA_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': True, 'count': len(rows), 'row': row}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
