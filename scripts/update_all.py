#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    print('+', ' '.join(cmd))
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise SystemExit(res.returncode)


def main():
    p = argparse.ArgumentParser(description='Refresh tracker artifacts')
    p.add_argument('--rebuild-baseline', action='store_true', help='Rebuild monthly baseline series before dashboard build')
    args = p.parse_args()

    if args.rebuild_baseline:
        run([sys.executable, 'scripts/build_baseline_series.py'])
    run([sys.executable, 'scripts/build_dashboard.py'])
    print('\nDone: observations -> series_cache -> docs/index.html refreshed')


if __name__ == '__main__':
    main()
