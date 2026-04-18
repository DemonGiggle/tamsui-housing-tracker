#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/gigo/.openclaw/projects/tamsui-housing-tracker"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

cd "$ROOT"

echo "[$(date '+%F %T')] weekly refresh start"
python3 scripts/update_all.py | tee -a "$LOG_DIR/weekly-refresh.log"
echo "[$(date '+%F %T')] weekly refresh done"
