"""vuln defaultcreds — search default credential list by vendor/device/protocol."""
from __future__ import annotations
import json, sys
from pathlib import Path

DATA = Path(__file__).parent.parent.parent / "data" / "defaultcreds.json"

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: vuln defaultcreds <keyword>"); return 1
    kw      = " ".join(argv).lower()
    devices = json.loads(DATA.read_text())["devices"]
    hits    = [d for d in devices if
               kw in d["vendor"].lower() or
               kw in d["device"].lower() or
               any(kw in p.lower() for p in d["protocol"])]
    if not hits:
        print(f"No default credentials found for '{kw}'"); return 0
    print(f"Default creds matching '{kw}'  ({len(hits)} entries):")
    print(f"  {'Vendor':<20} {'Device':<28} {'Proto':<12} {'User':<18} Password")
    print(f"  {'-'*20} {'-'*28} {'-'*12} {'-'*18} --------")
    for d in hits:
        print(f"  {d['vendor']:<20} {d['device']:<28} "
              f"{','.join(d['protocol']):<12} "
              f"{(d['username'] or '(blank)'):<18} "
              f"{d['password'] or '(blank)'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
