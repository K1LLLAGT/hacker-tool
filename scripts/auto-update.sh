#!/usr/bin/env bash
# auto-update.sh — delegates to htctl update if available, falls back to raw git
set -euo pipefail

HT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$HT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/auto-update-$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] auto-update triggered" >> "$LOG"

if command -v htctl &>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] delegating to htctl update" >> "$LOG"
    htctl update >> "$LOG" 2>&1
else
    # Fallback: raw git with auto-stash
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] htctl not found — raw git pull" >> "$LOG"
    cd "$HT_ROOT"
    if ! git diff --quiet || ! git diff --cached --quiet; then
        STASH="bootstrap-autostash-$(date +%Y%m%d-%H%M%S)"
        git stash push -m "$STASH" >> "$LOG" 2>&1
        git pull --ff-only >> "$LOG" 2>&1 || git rebase origin/main >> "$LOG" 2>&1
        git stash pop >> "$LOG" 2>&1 || echo "[WARN] stash pop conflict — stash preserved" >> "$LOG"
    else
        git pull --ff-only >> "$LOG" 2>&1 || git rebase origin/main >> "$LOG" 2>&1
    fi
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] done" >> "$LOG"
