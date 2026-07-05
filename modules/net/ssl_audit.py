"""
net/ssl_audit.py — TLS certificate & handshake audit (stdlib ssl).

Reports cert subject/issuer, validity window and days-to-expiry, SANs, the
negotiated protocol + cipher, and whether the site sends HSTS.

    python modules/net/ssl_audit.py example.com
    python modules/net/ssl_audit.py example.com:8443
    python modules/net/ssl_audit.py example.com --no-verify   # inspect anyway
"""
from __future__ import annotations

import argparse
import datetime as _dt
import socket
import ssl
import sys


def _parse_cert_time(value: str) -> _dt.datetime:
    # OpenSSL format: 'Jun  1 12:00:00 2026 GMT'
    return _dt.datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(
        tzinfo=_dt.timezone.utc)


def _decode_untrusted(der: bytes) -> dict:
    """Get a getpeercert()-style dict for a cert we didn't verify.

    stdlib only populates the cert dict on the verified path, so for
    --no-verify we decode the DER ourselves via a temp PEM file.
    """
    import os
    import tempfile
    pem = ssl.DER_cert_to_PEM_cert(der)
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(pem)
        return ssl._ssl._test_decode_cert(path)  # stable stdlib helper
    except Exception:
        return {}
    finally:
        os.unlink(path)


def _flatten(pairs) -> dict:
    out: dict[str, str] = {}
    for rdn in pairs or ():
        for k, v in rdn:
            out[k] = v
    return out


def audit(host: str, port: int = 443, timeout: float = 6.0,
          verify: bool = True) -> dict:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    result: dict = {"host": host, "port": port, "verified": verify}
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            result["protocol"] = tls.version()
            cipher = tls.cipher()
            result["cipher"] = cipher[0] if cipher else None
            result["cipher_bits"] = cipher[2] if cipher else None
            cert = tls.getpeercert() if verify else \
                _decode_untrusted(tls.getpeercert(binary_form=True))

    if not cert:
        result.update({"subject_cn": None, "issuer_cn": None,
                       "not_after": None, "days_to_expiry": None,
                       "expired": False, "not_yet_valid": False, "sans": []})
        result["hsts"] = _check_hsts(host, port, timeout)
        return result

    subj = _flatten(cert.get("subject"))
    issuer = _flatten(cert.get("issuer"))
    not_after = _parse_cert_time(cert["notAfter"])
    not_before = _parse_cert_time(cert["notBefore"])
    now = _dt.datetime.now(_dt.timezone.utc)

    result.update({
        "subject_cn": subj.get("commonName"),
        "issuer_cn": issuer.get("commonName") or issuer.get("organizationName"),
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "days_to_expiry": (not_after - now).days,
        "expired": now > not_after,
        "not_yet_valid": now < not_before,
        "sans": [v for t, v in cert.get("subjectAltName", ()) if t == "DNS"],
    })
    result["hsts"] = _check_hsts(host, port, timeout)
    return result


def _check_hsts(host: str, port: int, timeout: float) -> bool | None:
    """Best-effort: HEAD / over TLS and look for Strict-Transport-Security."""
    try:
        import http.client
        conn = http.client.HTTPSConnection(host, port, timeout=timeout,
                                            context=ssl._create_unverified_context())
        conn.request("HEAD", "/", headers={"User-Agent": "hacker-tool/ssl_audit"})
        resp = conn.getresponse()
        val = resp.getheader("Strict-Transport-Security")
        conn.close()
        return val is not None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net ssl-audit", description="TLS/cert audit.")
    ap.add_argument("target", help="host or host:port (default port 443)")
    ap.add_argument("--no-verify", action="store_true",
                    help="don't validate the chain (still inspects the cert)")
    ap.add_argument("--timeout", type=float, default=6.0)
    args = ap.parse_args(argv)

    host, _, port_s = args.target.partition(":")
    port = int(port_s) if port_s else 443

    try:
        r = audit(host, port, args.timeout, verify=not args.no_verify)
    except ssl.SSLCertVerificationError as e:
        print(f"[ssl] verification failed: {e}", file=sys.stderr)
        print("      re-run with --no-verify to inspect the cert anyway",
              file=sys.stderr)
        return 2
    except (socket.gaierror, socket.timeout, ConnectionError, OSError) as e:
        print(f"[ssl] connection error: {e}", file=sys.stderr)
        return 2

    days = r["days_to_expiry"]
    warn = ("  <-- EXPIRED" if r["expired"] else
            "  <-- expires soon" if (days is not None and days < 21) else "")
    print(f"host        {r['host']}:{r['port']}  ({'verified' if r['verified'] else 'UNVERIFIED'})")
    print(f"protocol    {r['protocol']}   cipher {r['cipher']} ({r['cipher_bits']} bit)")
    print(f"subject CN  {r['subject_cn']}")
    print(f"issuer      {r['issuer_cn']}")
    print(f"valid       {r.get('not_before')}  ->  {r['not_after']}")
    print(f"expiry      {days if days is not None else '?'} days{warn}")
    print(f"HSTS        {'yes' if r['hsts'] else ('no' if r['hsts'] is False else 'unknown')}")
    if r["sans"]:
        print(f"SANs        {', '.join(r['sans'][:12])}"
              + (f"  (+{len(r['sans']) - 12} more)" if len(r["sans"]) > 12 else ""))
    return 1 if (r["expired"] or r["not_yet_valid"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
