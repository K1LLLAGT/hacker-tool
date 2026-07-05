#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HT_ROOT="$HOME/hacker-tool"
LOG_DIR="$HT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly-$(date +%Y%m%d).log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] nightly scan started" >> "$LOG"

# Rootless gateway: UDP socket trick (confirmed working on Android 16)
GW=$(python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    print(ip.rsplit('.', 1)[0] + '.1')
except Exception:
    pass
")

# Config override takes priority
if [[ -f "$HOME/.config/hacker-tool/gateway" ]]; then
    GW=$(cat "$HOME/.config/hacker-tool/gateway")
fi

if [[ -z "$GW" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No gateway detected — skipping" >> "$LOG"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gateway: $GW" >> "$LOG"
python3 "$HT_ROOT/modules/net/pipeline.py" \
    "$GW" --top-ports 50 --save --notify >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] done" >> "$LOG"
find "$LOG_DIR" -name "nightly-*.log" -mtime +7 -delete
