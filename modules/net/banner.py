"""
net/banner.py — TCP service banner grabber (stdlib socket).

Connects to one host across one or more ports, optionally sends a probe, and
reads whatever the service announces. Single-target by design — this is service
identification, not a mass scanner.

    python modules/net/banner.py 10.0.0.1
    python modules/net/banner.py example.com -p 22,80,443
    python modules/net/banner.py 10.0.0.1 -p 8080 --probe "GET / HTTP/1.0\r\n\r\n"
"""
from __future__ import annotations

import argparse
import socket
import sys

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 587, 993, 3306, 5432, 8080]

# Ports that stay silent until spoken to first.
_DEFAULT_PROBES = {
    80: "HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n",
    8080: "HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n",
    443: "",   # TLS; a plaintext probe won't help, just note it's open
}


def grab(host: str, port: int, timeout: float = 3.0,
         probe: str | None = None) -> dict:
    info: dict = {"port": port, "open": False, "banner": None, "error": None}
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            info["open"] = True
            s.settimeout(timeout)
            send = probe if probe is not None else _DEFAULT_PROBES.get(port)
            if send:
                s.sendall(send.format(host=host).encode("latin-1", "ignore"))
            try:
                data = s.recv(1024)
            except socket.timeout:
                data = b""
            text = data.decode("latin-1", "replace").strip()
            info["banner"] = text.splitlines()[0] if text else None
    except (socket.timeout, ConnectionRefusedError) as e:
        info["error"] = type(e).__name__
    except OSError as e:
        info["error"] = str(e)
    return info


def _parse_ports(spec: str) -> list[int]:
    ports: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            ports.extend(range(int(a), int(b) + 1))
        elif chunk:
            ports.append(int(chunk))
    return ports


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net banner", description="Grab TCP banners.")
    ap.add_argument("host", help="single target host or IP")
    ap.add_argument("-p", "--ports", help="e.g. 22,80,443 or 8000-8010 (default: common)")
    ap.add_argument("--probe", help="raw bytes to send first (\\r\\n understood, {host} expanded)")
    ap.add_argument("--timeout", type=float, default=3.0)
    args = ap.parse_args(argv)

    ports = _parse_ports(args.ports) if args.ports else COMMON_PORTS
    probe = args.probe.encode().decode("unicode_escape") if args.probe else None

    found = False
    for p in ports:
        r = grab(args.host, p, args.timeout, probe)
        if r["open"]:
            found = True
            banner = r["banner"] or "(open, no banner)"
            print(f"{args.host}:{p:<6} open   {banner}")
        elif args.ports:  # only report closed ports if user asked for specifics
            print(f"{args.host}:{p:<6} {r['error'] or 'closed'}", file=sys.stderr)
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
