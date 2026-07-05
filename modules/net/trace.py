"""
net/trace.py — traceroute wrapper (stdlib subprocess).

Real traceroute needs ICMP/raw sockets (root), so this wraps whichever tool is
present, in preference order: traceroute -> tracepath -> nmap --traceroute.
Parses hops into a uniform table.

    python modules/net/trace.py 1.1.1.1
    python modules/net/trace.py example.com --max-hops 20
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

_IP = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
_RTT = re.compile(r"(\d+(?:\.\d+)?)\s*ms")


def _tool() -> tuple[str, list[str]] | None:
    if shutil.which("traceroute"):
        return "traceroute", ["traceroute", "-n"]
    if shutil.which("tracepath"):
        return "tracepath", ["tracepath", "-n"]
    if shutil.which("nmap"):
        return "nmap", ["nmap", "-sn", "--traceroute", "-n"]
    return None


def trace(target: str, max_hops: int = 30, timeout: float = 60.0) -> list[dict]:
    picked = _tool()
    if picked is None:
        raise FileNotFoundError("traceroute/tracepath/nmap")
    name, base = picked
    if name == "traceroute":
        cmd = base + ["-m", str(max_hops), target]
    elif name == "tracepath":
        cmd = base + ["-m", str(max_hops), target]
    else:
        cmd = base + [target]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    hops: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        m = re.match(r"^(\d+)\b", line)
        if not m:
            continue
        ip_m = _IP.search(line)
        rtts = _RTT.findall(line)
        hops.append({
            "hop": int(m.group(1)),
            "ip": ip_m.group(0) if ip_m else ("*" if "*" in line else None),
            "rtt_ms": min(float(x) for x in rtts) if rtts else None,
        })
    return hops


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net trace", description="Traceroute to a host.")
    ap.add_argument("target")
    ap.add_argument("--max-hops", type=int, default=30)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args(argv)

    try:
        hops = trace(args.target, args.max_hops, args.timeout)
    except FileNotFoundError:
        print("[trace] no traceroute tool found — `pkg install traceroute` "
              "(or nmap)", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("[trace] timed out", file=sys.stderr)
        return 2

    if not hops:
        print("[trace] no hops parsed (target may be unreachable)", file=sys.stderr)
        return 1
    for h in hops:
        rtt = f"{h['rtt_ms']:.1f} ms" if h["rtt_ms"] is not None else "*"
        print(f"{h['hop']:>3}  {h['ip'] or '*':<16} {rtt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
