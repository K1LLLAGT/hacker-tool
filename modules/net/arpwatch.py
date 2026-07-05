"""
net arpwatch — periodic LAN sweep, detect new devices, OUI resolve, auto-pipeline.

Android 16 rootless design:
  - Host discovery : parallel ping + Python TCP connect (no raw sockets)
  - MAC resolution : arp -a after ping (graceful skip if blocked)
  - OUI lookup     : data/oui.json (offline, no internet)
  - State tracking : reports/arpwatch_state.json
  - Auto-scan      : triggers net/pipeline.py on every new IP

Usage:
    hackertool net arpwatch scan          # one-shot sweep + report new devices
    hackertool net arpwatch watch [--interval N]  # continuous loop (default 120s)
    hackertool net arpwatch list          # show known device table
    hackertool net arpwatch clear         # wipe known-hosts state (fresh start)
    hackertool net arpwatch scan --no-pipeline  # sweep only, skip auto-scan
"""
from __future__ import annotations
import json, socket, subprocess, sys, datetime, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
OUI_DB    = ROOT / "data"    / "oui.json"
STATE_F   = ROOT / "reports" / "arpwatch_state.json"
PIPE_MOD  = ROOT / "modules" / "net" / "pipeline.py"
PID_FILE  = ROOT / "logs"    / "arpwatch.pid"

# ── Network helpers ────────────────────────────────────────────────────

def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""

def subnet_hosts(base_ip: str, prefix: int = 24) -> list[str]:
    """Generate all host IPs in a /24 (or smaller) subnet."""
    octets = base_ip.split(".")
    if len(octets) != 4:
        return []
    net = ".".join(octets[:3])
    return [f"{net}.{i}" for i in range(1, 255)]

# ── Host discovery ─────────────────────────────────────────────────────

def _ping(ip: str) -> str | None:
    """ICMP ping via system binary — allowed on Android without root."""
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True, timeout=3
        )
        return ip if r.returncode == 0 else None
    except Exception:
        return None

def _tcp_probe(ip: str, ports: list[int] = (80, 443, 22, 53, 8080)) -> str | None:
    """TCP connect fallback — if any common port responds, host is live."""
    for port in ports:
        try:
            with socket.create_connection((ip, port), timeout=0.8):
                return ip
        except (ConnectionRefusedError, OSError):
            continue
        except Exception:
            continue
    return None

def sweep(hosts: list[str], workers: int = 80) -> list[str]:
    """Parallel sweep: ping first, TCP probe as fallback for non-responders."""
    live: set[str] = set()
    pinged_dead: list[str] = []

    # Round 1: ping all hosts
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for result in as_completed({ex.submit(_ping, h): h for h in hosts}):
            r = result.result()
            if r:
                live.add(r)
            else:
                pinged_dead.append(result._args[0] if hasattr(result, '_args') else "")

    # Round 2: TCP probe anything ping missed (firewalled hosts)
    not_seen = [h for h in hosts if h not in live]
    if not_seen:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for result in as_completed({ex.submit(_tcp_probe, h): h for h in not_seen}):
                r = result.result()
                if r:
                    live.add(r)

    return sorted(live, key=lambda x: int(x.split(".")[-1]))

# ── MAC / OUI resolution ───────────────────────────────────────────────

def get_mac(ip: str) -> str:
    """
    Attempt to read MAC from ARP table after host discovery.
    Tries arp -a, arp -n, and /proc/net/arp — skips gracefully if all blocked.
    """
    # Method A: arp -a (most likely to work on Termux)
    for cmd in (["arp", "-a", ip], ["arp", "-n", ip]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                parts = line.split()
                for part in parts:
                    # MAC format: xx:xx:xx:xx:xx:xx
                    if len(part) == 17 and part.count(":") == 5:
                        return part.upper()
        except Exception:
            pass

    # Method B: /proc/net/arp (blocked on Android 16, skip silently)
    try:
        for line in open("/proc/net/arp").read().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == ip:
                mac = parts[3]
                if mac != "00:00:00:00:00:00":
                    return mac.upper()
    except Exception:
        pass

    return ""

def oui_lookup(mac: str) -> str:
    """Look up vendor from data/oui.json using the first 3 octets (OUI prefix)."""
    if not mac or len(mac) < 8:
        return "Unknown"
    try:
        db   = json.loads(OUI_DB.read_text()) if OUI_DB.exists() else {}
        oui  = mac[:8].upper()          # e.g. "B8:27:EB"
        # Try colons, then dashes
        for fmt in (oui, oui.replace(":", "-")):
            if fmt in db:
                return db[fmt]
        # Partial match (first 6 hex chars)
        short = mac.replace(":", "").upper()[:6]
        for key, val in db.items():
            if key.replace(":", "").replace("-", "").upper()[:6] == short:
                return val
    except Exception:
        pass
    return "Unknown"

# ── State persistence ──────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_F.exists():
        try:
            return json.loads(STATE_F.read_text())
        except Exception:
            pass
    return {"known": {}, "history": []}

def save_state(state: dict) -> None:
    STATE_F.parent.mkdir(exist_ok=True)
    STATE_F.write_text(json.dumps(state, indent=2))

# ── Pipeline trigger ───────────────────────────────────────────────────

def trigger_pipeline(ip: str) -> None:
    """Fire net/pipeline.py against newly discovered IP."""
    print(f"  [arpwatch] ⚡ Triggering pipeline scan on {ip}...")
    try:
        subprocess.Popen(
            [sys.executable, str(PIPE_MOD), ip, "--top-ports", "50", "--save", "--notify"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"  [arpwatch] Pipeline started for {ip} (background)")
    except Exception as e:
        print(f"  [arpwatch] Pipeline launch failed: {e}")

# ── Notification ───────────────────────────────────────────────────────

def notify(title: str, msg: str) -> None:
    try:
        subprocess.run(
            ["termux-notification", "--title", title,
             "--content", msg, "--sound", "--vibrate", "300"],
            timeout=5, capture_output=True
        )
    except Exception:
        pass

# ── Core scan logic ────────────────────────────────────────────────────

def run_scan(auto_pipeline: bool = True, quiet: bool = False) -> dict:
    """Full sweep cycle: discover → resolve → diff → report → trigger."""
    my_ip = local_ip()
    if not my_ip:
        print("[arpwatch] Cannot determine local IP"); return {}

    hosts    = subnet_hosts(my_ip)
    ts       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state    = load_state()
    known    = state.get("known", {})

    if not quiet:
        subnet = my_ip.rsplit(".", 1)[0] + ".0/24"
        print(f"[arpwatch] {ts} — sweeping {subnet} ({len(hosts)} hosts)...")

    live = sweep(hosts)

    if not quiet:
        print(f"[arpwatch] {len(live)} host(s) up  |  {len(known)} previously known")

    new_devices   = []
    gone_devices  = []
    current_round = {}

    # Resolve MACs and OUI for all live hosts
    for ip in live:
        mac    = get_mac(ip)
        vendor = oui_lookup(mac) if mac else "Unknown"
        is_new = ip not in known
        current_round[ip] = {
            "mac":       mac or "—",
            "vendor":    vendor,
            "first_seen": known.get(ip, {}).get("first_seen", ts) if not is_new else ts,
            "last_seen":  ts,
            "scan_count": known.get(ip, {}).get("scan_count", 0) + 1,
        }
        if is_new:
            new_devices.append(ip)
            if not quiet:
                print(f"  [NEW] {ip:<16}  MAC: {mac or '—':<19}  Vendor: {vendor}")

    # Devices that disappeared
    for ip in known:
        if ip not in current_round:
            gone_devices.append(ip)
            if not quiet:
                print(f"  [GONE] {ip:<15}  was: {known[ip].get('vendor','?')}")

    if not new_devices and not gone_devices and not quiet:
        print("[arpwatch] No changes detected.")

    # Update state
    state["known"] = current_round
    state["history"].append({
        "ts":       ts,
        "live":     len(live),
        "new":      new_devices,
        "gone":     gone_devices,
        "my_ip":    my_ip,
    })
    # Keep last 500 history entries
    state["history"] = state["history"][-500:]
    save_state(state)

    # Notify + trigger pipeline for new devices
    if new_devices:
        notify(
            "arpwatch: New device(s) detected",
            f"{len(new_devices)} new on LAN: {', '.join(new_devices)}"
        )
        if auto_pipeline:
            for ip in new_devices:
                trigger_pipeline(ip)

    return {
        "ts": ts, "live": live, "new": new_devices,
        "gone": gone_devices, "my_ip": my_ip,
    }

# ── Commands ───────────────────────────────────────────────────────────

def cmd_list() -> int:
    state = load_state()
    known = state.get("known", {})
    if not known:
        print("No known hosts yet. Run: hackertool net arpwatch scan")
        return 0
    print(f"{'IP':<18} {'MAC':<20} {'Vendor':<28} {'First Seen':<20} Scans")
    print(f"{'--':<18} {'---':<20} {'------':<28} {'----------':<20} -----")
    for ip, info in sorted(known.items(),
                           key=lambda x: int(x[0].split(".")[-1])):
        print(f"{ip:<18} {info.get('mac','—'):<20} {info.get('vendor','?'):<28} "
              f"{info.get('first_seen','?')[:16]:<20} {info.get('scan_count',1)}")
    h = state.get("history", [])
    if h:
        last = h[-1]
        print(f"\nLast sweep: {last['ts']}  |  "
              f"Live: {last['live']}  |  "
              f"New: {len(last['new'])}  |  "
              f"Gone: {len(last['gone'])}")
    return 0

def cmd_watch(interval: int, auto_pipeline: bool) -> int:
    print(f"[arpwatch] Starting continuous watch (interval={interval}s). Ctrl+C to stop.")
    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text(str(__import__("os").getpid()))
    try:
        while True:
            run_scan(auto_pipeline=auto_pipeline)
            print(f"[arpwatch] Sleeping {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[arpwatch] Stopped.")
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd  = argv[0] if argv else "scan"

    no_pipeline = "--no-pipeline" in argv
    quiet       = "--quiet" in argv

    if cmd == "scan":
        result = run_scan(auto_pipeline=not no_pipeline, quiet=quiet)
        if result.get("new"):
            print(f"\n[arpwatch] {len(result['new'])} new device(s): {', '.join(result['new'])}")
        return 0

    if cmd == "watch":
        interval = 120
        for i, a in enumerate(argv):
            if a == "--interval" and i + 1 < len(argv):
                interval = int(argv[i + 1])
        return cmd_watch(interval, auto_pipeline=not no_pipeline)

    if cmd == "list":
        return cmd_list()

    if cmd == "clear":
        STATE_F.unlink(missing_ok=True)
        print("[arpwatch] State cleared — all known hosts reset.")
        return 0

    if cmd == "status":
        if PID_FILE.exists():
            pid = PID_FILE.read_text().strip()
            print(f"[arpwatch] Watch daemon running (PID {pid})")
        else:
            print("[arpwatch] No watch daemon running.")
        state = load_state()
        known = state.get("known", {})
        h     = state.get("history", [])
        print(f"  Known hosts : {len(known)}")
        print(f"  Sweep count : {len(h)}")
        if h:
            print(f"  Last sweep  : {h[-1]['ts']}")
            print(f"  Last new    : {h[-1]['new'] or 'none'}")
        return 0

    print(f"Unknown command '{cmd}'. Use: scan, watch, list, clear, status")
    return 1

if __name__ == "__main__":
    sys.exit(main())
