"""vuln ciphers — flag deprecated TLS ciphers/protocols from ssl_audit JSON."""
from __future__ import annotations
import json, sys
from pathlib import Path

WEAK_PROTOS  = {"SSLv2","SSLv3","TLSv1","TLSv1.0","TLSv1.1"}
WEAK_CIPHERS = {"RC4","DES","3DES","EXPORT","NULL","IDEA","SEED","ADH","AECDH","RC2","ARCFOUR"}

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    data = {}
    if argv and Path(argv[0]).exists():
        data = json.loads(Path(argv[0]).read_text())
    elif not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        print("Usage: vuln ciphers <ssl_audit.json>"); return 1
    issues = []
    proto = data.get("protocol", data.get("version", ""))
    if proto in WEAK_PROTOS:
        issues.append(f"CRITICAL: Deprecated protocol — {proto}")
    for c in data.get("ciphers", []):
        name = c if isinstance(c, str) else c.get("name", "")
        for wc in WEAK_CIPHERS:
            if wc in name.upper():
                issues.append(f"WARN: Weak cipher component '{wc}' in {name}"); break
    if not issues:
        print("No deprecated ciphers or protocols detected."); return 0
    print(f"Issues found ({len(issues)}):")
    for i in issues: print(f"  {i}")
    print("\nRemediation: disable TLS<1.2, remove RC4/DES/NULL/EXPORT suites, enforce TLS 1.3")
    return 1

if __name__ == "__main__":
    sys.exit(main())
