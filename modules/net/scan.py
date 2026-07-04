"""
modules/net/scan.py — thin wrappers around nmap/ping for LAN inventory.

Intended use: mapping devices on YOUR OWN network (e.g. confirming the
Pi 5's DHCP-assigned IP, checking what's alive on 192.168.1.0/24).
This module does not perform vulnerability scanning, exploitation, or
scanning of hosts outside a locally-scoped private range — it's an
inventory/audit tool, not an attack tool.
"""
import ipaddress
import shutil
import subprocess


PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


def _is_private_range(cidr: str) -> bool:
    net = ipaddress.ip_network(cidr, strict=False)
    return any(net.subnet_of(r) or net == r for r in PRIVATE_RANGES)


def ping_sweep(cidr: str, timeout_s: float = 1.0) -> list:
    """Simple ping sweep — works even without nmap installed."""
    if not _is_private_range(cidr):
        raise ValueError(
            f"{cidr} is not a private/local range. This tool only scans "
            "RFC1918 ranges (your own LAN)."
        )
    net = ipaddress.ip_network(cidr, strict=False)
    alive = []
    ping_bin = shutil.which("ping")
    if not ping_bin:
        raise RuntimeError("ping not found on this system")

    for host in net.hosts():
        result = subprocess.run(
            [ping_bin, "-c", "1", "-W", str(int(timeout_s)), str(host)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            alive.append(str(host))
    return alive


def nmap_scan(cidr: str, extra_args: list = None) -> str:
    """Delegates to nmap if installed; returns raw output text.
    Restricted to private ranges — see _is_private_range."""
    if not _is_private_range(cidr):
        raise ValueError(
            f"{cidr} is not a private/local range. This tool only scans "
            "RFC1918 ranges (your own LAN)."
        )
    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        raise RuntimeError(
            "nmap not found. Install with: pkg install nmap (Termux) / "
            "apt install nmap (Kali)"
        )
    args = [nmap_bin, "-sn"] + (extra_args or []) + [cidr]  # -sn = ping scan, host discovery only
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"nmap failed: {result.stderr.strip()}")
    return result.stdout


def main(argv: list[str]) -> int:
    """CLI entry point: inventory hosts on a private (RFC1918) CIDR."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        prog="net-scan",
        description="Discover live hosts on a private CIDR (your own LAN).")
    parser.add_argument(
        "cidr", help="Private CIDR to sweep, e.g. 192.168.1.0/24.")
    parser.add_argument(
        "-m", "--method", choices=("ping", "nmap"), default="ping",
        help="Discovery method: 'ping' (no deps) or 'nmap -sn'. "
             "Default: ping.")
    parser.add_argument(
        "-t", "--timeout", type=float, default=1.0,
        help="Per-host timeout in seconds for the ping sweep.")
    args = parser.parse_args(argv)

    try:
        if args.method == "nmap":
            print(nmap_scan(args.cidr))
        else:
            alive = ping_sweep(args.cidr, timeout_s=args.timeout)
            print(json.dumps(
                {"cidr": args.cidr, "alive": alive, "count": len(alive)},
                indent=2))
    except (ValueError, RuntimeError) as exc:
        print(f"net-scan: {exc}", file=sys.stderr)
        return 1
    return 0
