"""net pipeline — scan → CVE → default-cred auto-report."""
from __future__ import annotations
import json, subprocess, sys, datetime
from pathlib import Path

ROOT    = Path(__file__).parent.parent.parent
CVE_DB  = ROOT / "data" / "cve.json"
CRED_DB = ROOT / "data" / "defaultcreds.json"
PROTO   = {"21":"ftp","22":"ssh","23":"telnet","25":"smtp","80":"http",
           "110":"pop3","143":"imap","443":"https","445":"smb","1433":"mssql",
           "3306":"mysql","3389":"rdp","5432":"postgres","5900":"vnc",
           "6379":"redis","8080":"http","27017":"mongodb"}

def scan(target: str, top: int) -> list[str]:
    print(f"\n[pipeline] Scanning {target} (top {top} ports)...")
    try:
        r = subprocess.run(["nmap","-T4",f"--top-ports={top}","--open","-oG","-",target],
                           capture_output=True, text=True, timeout=120)
        return [p.split("/")[0] for line in r.stdout.splitlines()
                if "Ports:" in line for p in line.split() if "/open/" in p]
    except Exception as e:
        print(f"[pipeline] Scan error: {e}"); return []

def notify(msg: str) -> None:
    try:
        subprocess.run(["termux-notification","--title","hacker-tool pipeline",
                        "--content", msg], timeout=5, capture_output=True)
    except Exception:
        pass

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: net pipeline <target> [--top-ports N] [--save] [--notify]"); return 1

    target    = argv[0]
    top_ports = 100
    save      = "--save"   in argv
    do_notify = "--notify" in argv
    for i, a in enumerate(argv):
        if a == "--top-ports" and i+1 < len(argv):
            top_ports = int(argv[i+1])

    cve_db  = json.loads(CVE_DB.read_text())  if CVE_DB.exists()  else {"ports":{}}
    cred_db = json.loads(CRED_DB.read_text()) if CRED_DB.exists() else {"devices":[]}

    ports = scan(target, top_ports)
    if not ports:
        print("[pipeline] No open ports found."); return 1
    print(f"[pipeline] Open: {', '.join(ports)}")

    # CVE hits
    cve_hits = {}
    for p in ports:
        info = cve_db["ports"].get(p)
        if info:
            cve_hits[p] = {"service": info["service"],
                           "count":   len(info["cves"]),
                           "max":     max(c["cvss"] for c in info["cves"]),
                           "top":     max(info["cves"], key=lambda c: c["cvss"]),
                           "risks":   info["risks"]}

    # Default cred hits
    cred_hits = {}
    devices   = cred_db["devices"]
    for p in ports:
        proto = PROTO.get(p)
        if not proto: continue
        m = [d for d in devices if proto in d.get("protocol",[])]
        if m: cred_hits[p] = {"proto": proto, "count": len(m), "sample": m[:3]}

    # Print
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*62}")
    print(f"  PIPELINE REPORT — {target}  [{ts}]")
    print(f"  Open ports: {len(ports)}  |  CVE matches: {len(cve_hits)}  |  Default creds: {len(cred_hits)}")
    print(f"{'='*62}")

    print(f"\n── CVE Exposure ({'─'*48}")
    if cve_hits:
        for p,i in sorted(cve_hits.items(), key=lambda x:-x[1]["max"]):
            t = i["top"]
            print(f"  :{p:<6} {i['service']:<22} {i['count']} CVEs  max={i['max']}")
            print(f"           [{t['cvss']}] {t['id']} — {t['desc'][:65]}")
    else:
        print("  No CVE matches.")

    print(f"\n── Default Credential Risk ({'─'*38}")
    if cred_hits:
        for p,i in cred_hits.items():
            print(f"  :{p:<6} {i['proto']:<10} {i['count']} entries")
            for d in i["sample"]:
                u  = d["username"] or "(blank)"
                pw = d["password"] or "(blank)"
                print(f"           {d['vendor']:<20} {u}:{pw}")
    else:
        print("  No default credential matches.")

    critical = [p for p,i in cve_hits.items() if i["max"] >= 9.0]
    print(f"\n── Summary {'─'*52}")
    print(f"  Critical CVSS≥9.0  : {', '.join(critical) or 'none'}")
    print(f"  Default cred ports : {', '.join(cred_hits) or 'none'}")
    print(f"  Total open ports   : {len(ports)}")

    if save:
        out = ROOT/"reports"/f"pipeline_{target.replace('.','_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        (ROOT/"reports").mkdir(exist_ok=True)
        out.write_text(json.dumps({"target":target,"ts":ts,"ports":ports,
                                   "cve_hits":cve_hits,"cred_hits":cred_hits},indent=2))
        print(f"\n  Saved → {out}")

    if do_notify:
        summary = f"{len(ports)} ports open | {len(critical)} critical CVEs | {len(cred_hits)} default cred risks"
        notify(f"{target}: {summary}")
        print(f"  Notification sent.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
