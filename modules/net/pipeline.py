"""
net pipeline — scan → CVE → default-cred auto-report.
Rootless on Android: reads /proc/net/route for gateway, pure-Python
TCP connect scanner as fallback when nmap is unavailable/restricted.
Usage:
    hackertool net pipeline <target|gateway> [--top-ports N] [--ports a,b,c] [--save] [--notify]
"""
from __future__ import annotations
import json, socket, subprocess, sys, datetime, struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT    = Path(__file__).parent.parent.parent
CVE_DB  = ROOT / "data" / "cve.json"
CRED_DB = ROOT / "data" / "defaultcreds.json"
PROTO   = {
    "21":"ftp","22":"ssh","23":"telnet","25":"smtp","53":"dns",
    "80":"http","110":"pop3","143":"imap","161":"snmp","389":"ldap",
    "443":"https","445":"smb","1433":"mssql","1883":"mqtt",
    "3306":"mysql","3389":"rdp","5432":"postgres","5900":"vnc",
    "6379":"redis","8080":"http","8443":"https","9200":"http",
    "27017":"mongodb",
}

# Common top-100 ports (nmap's default list, abbreviated to 50 most relevant)
TOP50 = [
    21,22,23,25,53,80,110,111,135,139,143,161,389,443,445,
    512,513,514,554,631,993,995,1433,1723,1883,2049,3306,
    3389,4444,5432,5900,5985,6379,8080,8443,8888,9200,
    9300,10000,27017,27018,28017,3000,4000,4848,5000,
    7001,8000,8008,9090,
]

# ── Gateway detection ──────────────────────────────────────────────────

def _proc_net_route_gw() -> str:
    """Read default gateway from /proc/net/route — works on Android without root."""
    try:
        lines = Path("/proc/net/route").read_text().splitlines()
        for line in lines[1:]:          # skip header
            parts = line.split()
            if len(parts) < 3: continue
            dest    = parts[1]          # hex destination
            gateway = parts[2]          # hex gateway
            flags   = int(parts[3], 16) if len(parts) > 3 else 0
            # Default route: dest == 00000000, flags bit 0x2 = gateway
            if dest == "00000000" and (flags & 0x2):
                # Gateway is 4-byte little-endian hex → dotted decimal
                raw = bytes.fromhex(gateway)
                return ".".join(str(b) for b in reversed(raw))
    except Exception:
        pass
    return ""

def _termux_wifi_gw() -> str:
    """Fallback: termux-wifi-connectioninfo JSON (requires Termux:API app)."""
    try:
        r = subprocess.run(["termux-wifi-connectioninfo"],
                           capture_output=True, text=True, timeout=5)
        data = json.loads(r.stdout)
        return data.get("gateway", "") or data.get("ip_address", "").rsplit(".", 1)[0] + ".1"
    except Exception:
        pass
    return ""

def _getprop_gw() -> str:
    """Fallback: Android getprop for DHCP gateway on common interfaces."""
    for iface in ("wlan0", "eth0", "rmnet0", "rmnet_data0"):
        try:
            r = subprocess.run(["getprop", f"dhcp.{iface}.gateway"],
                               capture_output=True, text=True, timeout=3)
            gw = r.stdout.strip()
            if gw and gw != "": return gw
        except Exception:
            pass
    return ""

def get_gateway() -> str:
    """Try three rootless methods in order of reliability."""
    return _proc_net_route_gw() or _termux_wifi_gw() or _getprop_gw()

# ── Port scanning ──────────────────────────────────────────────────────

def _tcp_connect(host: str, port: int, timeout: float = 1.0) -> int | None:
    """Single TCP connect probe — returns port number if open, else None."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return port
    except (ConnectionRefusedError, OSError):
        return None

def python_scan(target: str, ports: list[int], workers: int = 64) -> list[str]:
    """Pure-Python threaded TCP connect scan — no root, no nmap."""
    open_ports = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_tcp_connect, target, p): p for p in ports}
        for f in as_completed(futures):
            result = f.result()
            if result is not None:
                open_ports.append(str(result))
    return sorted(open_ports, key=int)

def nmap_scan(target: str, top: int, port_str: str | None) -> list[str]:
    """nmap TCP connect scan (-sT) — no root. Returns empty list on any failure."""
    port_arg = [f"-p{port_str}"] if port_str else [f"--top-ports={top}"]
    cmd = ["nmap", "-sT", "-T4", "--open", "-oG", "-"] + port_arg + [target]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        found = []
        for line in r.stdout.splitlines():
            if "Ports:" in line:
                for token in line.split():
                    if "/open/" in token:
                        found.append(token.split("/")[0])
        return found
    except Exception:
        return []

def scan(target: str, top: int, port_str: str | None) -> list[str]:
    """Try nmap first; fall back to pure-Python scanner automatically."""
    print(f"[pipeline] Attempting nmap -sT scan on {target}...")
    result = nmap_scan(target, top, port_str)
    if result:
        print(f"[pipeline] nmap found {len(result)} open port(s).")
        return result
    # Fallback
    if port_str:
        ports = [int(p.strip()) for p in port_str.split(",") if p.strip().isdigit()]
    else:
        ports = TOP50[:top] if top <= len(TOP50) else TOP50
    print(f"[pipeline] Falling back to Python TCP scanner ({len(ports)} ports, 64 threads)...")
    result = python_scan(target, ports)
    print(f"[pipeline] Python scanner found {len(result)} open port(s).")
    return result

# ── CVE / Cred matching ────────────────────────────────────────────────

def cve_hits(ports: list[str], db: dict) -> dict:
    out = {}
    for p in ports:
        info = db.get("ports", {}).get(p)
        if info:
            out[p] = {
                "service": info["service"],
                "count":   len(info["cves"]),
                "max":     max(c["cvss"] for c in info["cves"]),
                "top":     max(info["cves"], key=lambda c: c["cvss"]),
                "risks":   info["risks"],
            }
    return out

def cred_hits(ports: list[str], db: dict) -> dict:
    devices = db.get("devices", [])
    out = {}
    for p in ports:
        proto = PROTO.get(p)
        if not proto: continue
        m = [d for d in devices if proto in d.get("protocol", [])]
        if m: out[p] = {"proto": proto, "count": len(m), "sample": m[:3]}
    return out

# ── Notification ───────────────────────────────────────────────────────

def notify(title: str, msg: str) -> None:
    try:
        subprocess.run(["termux-notification", "--title", title,
                        "--content", msg, "--sound", "--vibrate", "500"],
                       timeout=5, capture_output=True)
    except Exception:
        pass

# ── Report printer ─────────────────────────────────────────────────────

def print_report(target: str, ts: str, open_ports: list[str], cv: dict, cr: dict) -> None:
    print(f"\n{'='*64}")
    print(f"  PIPELINE REPORT — {target}  [{ts}]")
    print(f"  Open: {len(open_ports)}  |  CVE matches: {len(cv)}  |  Default creds: {len(cr)}")
    print(f"{'='*64}")

    print("\n── CVE Exposure ─────────────────────────────────────────────")
    if cv:
        for p, i in sorted(cv.items(), key=lambda x: -x[1]["max"]):
            t = i["top"]
            print(f"  :{p:<6} {i['service']:<22} {i['count']} CVEs  max={i['max']}")
            print(f"           [{t['cvss']}] {t['id']} — {t['desc'][:65]}")
    else:
        print("  No CVE data for discovered ports.")

    print("\n── Default Credential Risk ──────────────────────────────────")
    if cr:
        for p, i in cr.items():
            print(f"  :{p:<6} {i['proto']:<12} {i['count']} entries")
            for d in i["sample"]:
                u = d["username"] or "(blank)"; pw = d["password"] or "(blank)"
                print(f"           {d['vendor']:<20} {u}:{pw}")
    else:
        print("  No default credential matches.")

    critical = [p for p, i in cv.items() if i["max"] >= 9.0]
    print(f"\n── Summary ──────────────────────────────────────────────────")
    print(f"  Critical CVSS≥9.0  : {', '.join(critical) or 'none'}")
    print(f"  Default cred ports : {', '.join(cr) or 'none'}")
    print(f"  Total open ports   : {len(open_ports)}")

# ── Main ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: net pipeline <target|gateway> [--top-ports N] [--ports 22,80,443] [--save] [--notify]")
        return 1

    target    = argv[0]
    top_ports = 50
    port_list = None
    save      = "--save"   in argv
    do_notify = "--notify" in argv

    for i, a in enumerate(argv):
        if a == "--top-ports" and i + 1 < len(argv):
            top_ports = int(argv[i + 1])
        if a == "--ports" and i + 1 < len(argv):
            port_list = argv[i + 1]

    # Resolve gateway
    if target == "gateway":
        gw = get_gateway()
        if not gw:
            print("[pipeline] Gateway detection failed on all methods.")
            print("           Provide IP directly: net pipeline 192.168.1.1")
            print("           Or check: cat /proc/net/route")
            return 1
        print(f"[pipeline] Gateway: {gw}")
        target = gw

    cve_db  = json.loads(CVE_DB.read_text())  if CVE_DB.exists() else {}
    cred_db = json.loads(CRED_DB.read_text()) if CRED_DB.exists() else {}

    open_ports = scan(target, top_ports, port_list)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not open_ports:
        print(f"[pipeline] No open ports found on {target}.")
        print("           Is the host reachable? Try: python3 -c \"import socket; print(socket.create_connection(('{target}',80),2))\"")
        if do_notify: notify("hacker-tool", f"{target}: 0 ports open")
        return 0

    cv = cve_hits(open_ports, cve_db)
    cr = cred_hits(open_ports, cred_db)
    print_report(target, ts, open_ports, cv, cr)

    if save:
        out_dir = ROOT / "reports"
        out_dir.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out   = out_dir / f"pipeline_{target.replace('.','_')}_{stamp}.json"
        out.write_text(json.dumps({
            "target": target, "timestamp": ts,
            "open_ports": open_ports, "cve_hits": cv, "cred_hits": cr,
        }, indent=2))
        print(f"\n  Saved → {out}")

    if do_notify:
        critical = [p for p, i in cv.items() if i["max"] >= 9.0]
        summary  = (f"{len(open_ports)} ports | "
                    f"{len(critical)} critical CVE | "
                    f"{len(cr)} default cred risks")
        notify(f"Scan: {target}", summary)
        print("  Notification sent.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
