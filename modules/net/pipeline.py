"""
net pipeline — scan → CVE → default-cred auto-report.
Usage:
    hackertool net pipeline <target|gateway> [--top-ports N] [--ports a,b,c] [--save] [--notify]
"""
from __future__ import annotations
import json, subprocess, sys, datetime
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

def get_gateway() -> str:
    """Auto-detect default gateway via 'ip route show default'."""
    try:
        r = subprocess.run(["ip","route","show","default"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return ""

def scan(target: str, top: int, ports: str | None) -> list[str]:
    """TCP connect scan (-sT) — works without root on Termux/Android."""
    port_arg = [f"-p{ports}"] if ports else [f"--top-ports={top}"]
    cmd = ["nmap", "-sT", "-T4", "--open", "-oG", "-"] + port_arg + [target]
    print(f"[pipeline] nmap {' '.join(cmd[1:])}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        found = []
        for line in r.stdout.splitlines():
            if "Ports:" in line:
                for token in line.split():
                    if "/open/" in token:
                        found.append(token.split("/")[0])
        return found
    except subprocess.TimeoutExpired:
        print("[pipeline] Scan timed out"); return []
    except FileNotFoundError:
        print("[pipeline] nmap not found — install: pkg install nmap"); return []

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

def notify(title: str, msg: str) -> None:
    try:
        subprocess.run(["termux-notification",
                        "--title", title, "--content", msg,
                        "--sound", "--vibrate", "500"],
                       timeout=5, capture_output=True)
    except Exception:
        pass

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: net pipeline <target|gateway> [--top-ports N] [--ports 22,80,443] [--save] [--notify]")
        return 1

    target    = argv[0]
    top_ports = 100
    port_list = None
    save      = "--save"   in argv
    do_notify = "--notify" in argv

    # Resolve magic target
    if target == "gateway":
        gw = get_gateway()
        if not gw:
            print("[pipeline] Could not detect default gateway — specify IP manually"); return 1
        print(f"[pipeline] Gateway detected: {gw}")
        target = gw

    for i, a in enumerate(argv):
        if a == "--top-ports" and i + 1 < len(argv):
            top_ports = int(argv[i + 1])
        if a == "--ports" and i + 1 < len(argv):
            port_list = argv[i + 1]  # e.g. "22,80,443,3389"

    cve_db  = json.loads(CVE_DB.read_text())  if CVE_DB.exists()  else {}
    cred_db = json.loads(CRED_DB.read_text()) if CRED_DB.exists() else {}

    # Scan
    open_ports = scan(target, top_ports, port_list)
    if not open_ports:
        msg = f"[pipeline] No open ports found on {target}.\nTip: try --ports 22,80,443,445,3389,8080"
        print(msg)
        if do_notify: notify("hacker-tool", f"{target}: 0 ports open")
        return 0

    print(f"[pipeline] Open: {', '.join(open_ports)}")

    cv = cve_hits(open_ports, cve_db)
    cr = cred_hits(open_ports, cred_db)

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*64}")
    print(f"  PIPELINE REPORT — {target}  [{ts}]")
    print(f"  Open: {len(open_ports)}  |  CVE matches: {len(cv)}  |  Default creds: {len(cr)}")
    print(f"{'='*64}")

    print(f"\n── CVE Exposure ─────────────────────────────────────────────")
    if cv:
        for p, i in sorted(cv.items(), key=lambda x: -x[1]["max"]):
            t = i["top"]
            print(f"  :{p:<6} {i['service']:<22} {i['count']} CVEs  max={i['max']}")
            print(f"           [{t['cvss']}] {t['id']} — {t['desc'][:65]}")
    else:
        print("  No CVE data for discovered ports.")

    print(f"\n── Default Credential Risk ──────────────────────────────────")
    if cr:
        for p, i in cr.items():
            print(f"  :{p:<6} {i['proto']:<12} {i['count']} entries")
            for d in i["sample"]:
                u  = d["username"] or "(blank)"
                pw = d["password"] or "(blank)"
                print(f"           {d['vendor']:<20} {u}:{pw}")
    else:
        print("  No default credential matches.")

    critical = [p for p, i in cv.items() if i["max"] >= 9.0]
    print(f"\n── Summary ──────────────────────────────────────────────────")
    print(f"  Critical CVSS≥9.0  : {', '.join(critical) or 'none'}")
    print(f"  Default cred ports : {', '.join(cr) or 'none'}")
    print(f"  Total open ports   : {len(open_ports)}")

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
        summary = (f"{len(open_ports)} ports | "
                   f"{len(critical)} critical CVE | "
                   f"{len(cr)} default cred risk")
        notify(f"Scan: {target}", summary)
        print("  Notification sent.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
