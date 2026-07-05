#!/data/data/com.termux/files/usr/bin/bash
# arpwatch-daemon.sh — run arpwatch in background, log to logs/arpwatch.log
set -euo pipefail

HT_ROOT="$HOME/hacker-tool"
LOG="$HT_ROOT/logs/arpwatch.log"
PID="$HT_ROOT/logs/arpwatch.pid"
INTERVAL="${1:-120}"   # sweep interval in seconds, default 2 min

mkdir -p "$HT_ROOT/logs"

if [[ -f "$PID" ]] && kill -0 "$(cat "$PID")" 2>/dev/null; then
    echo "[arpwatch] Already running (PID $(cat "$PID"))"
    exit 0
fi

echo "[arpwatch] Starting daemon (interval=${INTERVAL}s) → $LOG"
nohup python3 "$HT_ROOT/modules/net/arpwatch.py" watch \
    --interval "$INTERVAL" >> "$LOG" 2>&1 &

echo $! > "$PID"
echo "[arpwatch] Daemon started — PID $(cat "$PID")"
echo "  Log  : $LOG"
echo "  Stop : htctl arpwatch-stop"
