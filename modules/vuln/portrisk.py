"""vuln portrisk — score open ports by exposure risk 0-100."""
from __future__ import annotations
import json, sys
from pathlib import Path

DATA = Path(__file__).parent.parent.parent / "data" / "cve.json"

RISK_WEIGHTS = {
    "Exposed to internet": 30, "No authentication": 25, "No auth": 25,
    "Cleartext": 20, "Default credentials": 20, "SMBv1": 25,
    "Root login": 15, "Brute force": 10, "Open relay": 20,
    "Anonymous": 15, "No TLS": 15, "xp_cmdshell": 25,
    "Lua sandbox": 20, "Investigate immediately": 30,
}

def grade(s: int) -> str:
    return ("CRITICAL" if s >= 80 else "HIGH    " if s >= 60 else
            "MEDIUM  " if s >= 40 else "LOW     " if s >= 20 else "INFO    ")

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    db   = json.loads(DATA.read_text()) if DATA.exists() else {"ports": {}}
    ports = argv or list(db["ports"].keys())
    rows = []
    for p in ports:
        info = db["ports"].get(str(p))
        if not info:
            rows.append((0, p, "Unknown", "INFO    ", "—")); continue
        score = int(max(c["cvss"] for c in info["cves"]) * 3) if info["cves"] else 0
        top_risk = "—"
        for risk in info.get("risks", []):
            for kw, pts in RISK_WEIGHTS.items():
                if kw.lower() in risk.lower():
                    score = min(score + pts, 100)
                    if top_risk == "—": top_risk = risk
                    break
        rows.append((score, p, info["service"], grade(score), top_risk))
    rows.sort(key=lambda x: -x[0])
    print(f"{'Port':<8} {'Service':<26} {'Grade':<10} {'Score':>5}  Top Risk")
    print(f"{'----':<8} {'-------':<26} {'-----':<10} {'-----':>5}  --------")
    for score, port, svc, g, risk in rows:
        print(f"{port:<8} {svc:<26} {g:<10} {score:>4}/100  {risk}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
