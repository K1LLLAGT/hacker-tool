#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HT_ROOT="$HOME/hacker-tool"
LOG_DIR="$HT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly-$(date +%Y%m%d).log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] nightly scan started" >> "$LOG"

# Rootless gateway detection: /proc/net/route (always readable on Android)
GW=$(python3 - << 'PYEOF'
from pathlib import Path
import struct
try:
    for line in Path("/proc/net/route").read_text().splitlines()[1:]:
        p = line.split()
        if len(p) >= 4 and p[1] == "00000000" and (int(p[3], 16) & 0x2):
            raw = bytes.fromhex(p[2])
            print(".".join(str(b) for b in reversed(raw)))
            break
except Exception:
    pass
PYEOF
)

# Fallback: getprop
if [[ -z "$GW" ]]; then
    for iface in wlan0 eth0 rmnet0 rmnet_data0; do
        GW=$(getprop "dhcp.${iface}.gateway" 2>/dev/null || true)
        [[ -n "$GW" ]] && break
    done
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
