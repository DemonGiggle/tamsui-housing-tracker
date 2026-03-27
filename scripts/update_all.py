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
    p.add_argument('--import-real', action='store_true', help='Run public-source importer before rebuilding dashboard')
    args = p.parse_args()

    if args.import_real:
        run([sys.executable, 'scripts/import_real_samples.py'])
    run([sys.executable, 'scripts/build_dashboard.py'])
    print('\nDone: observations -> series_cache -> docs/index.html refreshed')


if __name__ == '__main__':
    main()
