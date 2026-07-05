"""vuln cve — offline CVE lookup keyed by port, service, or keyword."""
from __future__ import annotations
import json, sys
from pathlib import Path

DATA = Path(__file__).parent.parent.parent / "data" / "cve.json"

def load() -> dict:
    if not DATA.exists():
        print(f"Error: {DATA} not found"); sys.exit(1)
    return json.loads(DATA.read_text())

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: vuln cve <port|service|list> [value ...]"); return 1
    db  = load()
    cmd = argv[0]
    if cmd == "list":
        print(f"Indexed ports ({len(db['ports'])}):")
        for p, info in sorted(db["ports"].items(), key=lambda x: int(x[0])):
            top = max(info["cves"], key=lambda c: c["cvss"])
            print(f"  {p:>5}  {info['service']:<30} {len(info['cves'])} CVEs  max={top['cvss']}")
        return 0
    if cmd == "service" and len(argv) > 1:
        kw   = argv[1].lower()
        hits = [cid for svc, cids in db.get("services", {}).items()
                if kw in svc.lower() for cid in cids]
        print(f"CVEs for '{argv[1]}': {', '.join(hits) or 'none found'}")
        return 0
    if cmd == "port":
        ports = argv[1:]
        if not ports:
            print("Specify ports: vuln cve port 22 80 443"); return 1
        for p in ports:
            info = db["ports"].get(str(p))
            if not info:
                print(f"  [{p}] No CVE data"); continue
            cves = sorted(info["cves"], key=lambda c: c["cvss"], reverse=True)
            print(f"\n── Port {p} / {info['service']} {'─'*40}")
            for c in cves:
                print(f"  [{c['cvss']:>4}] {c['id']}")
                print(f"         {c['desc']}")
            print("  Risks:")
            for r in info.get("risks", []): print(f"    ⚠  {r}")
        return 0
    print(f"Unknown command '{cmd}'. Use: port, service, list"); return 1

if __name__ == "__main__":
    sys.exit(main())
