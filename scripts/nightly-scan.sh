#!/data/data/com.termux/files/usr/bin/bash
# nightly-scan.sh — auto pipeline scan of gateway, saves report + notifies
set -euo pipefail

HT_ROOT="$HOME/hacker-tool"
LOG_DIR="$HT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly-$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] nightly scan started" >> "$LOG"

# Detect gateway
GW=$(ip route show default 2>/dev/null | awk '/via/{print $3; exit}')
if [[ -z "$GW" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No gateway detected — skipping" >> "$LOG"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gateway: $GW" >> "$LOG"

python3 "$HT_ROOT/modules/net/pipeline.py" \
    "$GW" \
    --top-ports 100 \
    --save \
    --notify \
    >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] done" >> "$LOG"

# Keep only last 7 days of logs
find "$LOG_DIR" -name "nightly-*.log" -mtime +7 -delete
