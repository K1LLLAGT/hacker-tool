"""
web/ssl_check.py — quick cert-expiry check (stdlib ssl).

Deliberately lightweight: days-to-expiry, valid-until, SAN count. For the full
issuer/cipher/HSTS breakdown use `net-ssl_audit` instead — this is the fast
"is my cert about to lapse?" check for monitoring/cron.

    python modules/web/ssl_check.py example.com
    python modules/web/ssl_check.py example.com:8443 --warn 30
"""
from __future__ import annotations

import argparse
import datetime as _dt
import socket
import ssl
import sys


def days_left(host: str, port: int = 443, timeout: float = 8.0) -> dict:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
    not_after = _dt.datetime.strptime(
        cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=_dt.timezone.utc)
    now = _dt.datetime.now(_dt.timezone.utc)
    sans = [v for t, v in cert.get("subjectAltName", ()) if t == "DNS"]
    return {"host": host, "port": port, "not_after": not_after.isoformat(),
            "days_left": (not_after - now).days, "san_count": len(sans)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web ssl-check", description="Cert expiry check.")
    ap.add_argument("target", help="host or host:port (default 443)")
    ap.add_argument("--warn", type=int, default=21, help="exit 1 if fewer days remain")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args(argv)

    host, _, port_s = args.target.partition(":")
    port = int(port_s) if port_s else 443
    try:
        r = days_left(host, port, args.timeout)
    except ssl.SSLCertVerificationError as e:
        print(f"[ssl-check] chain/verify error: {e}", file=sys.stderr)
        return 2
    except (socket.gaierror, socket.timeout, ConnectionError, OSError) as e:
        print(f"[ssl-check] {e}", file=sys.stderr)
        return 2

    flag = "  <-- BELOW THRESHOLD" if r["days_left"] < args.warn else ""
    print(f"{r['host']}:{r['port']}  expires {r['not_after']}  "
          f"({r['days_left']} days, {r['san_count']} SANs){flag}")
    return 1 if r["days_left"] < args.warn else 0


if __name__ == "__main__":
    raise SystemExit(main())
