"""
net/arpwatch.py — ARP neighbour snapshot & change detection (iproute2).

Uses `ip neigh show` (proot-safe — no raw sockets) to capture the IP<->MAC
table, saves a baseline, and on later runs flags:
  * NEW      — an IP/MAC not seen before
  * GONE     — a previously-seen entry now absent
  * CHANGED  — an IP whose MAC changed  (classic ARP-spoofing signal)

    python modules/net/arpwatch.py                 # snapshot + diff vs baseline
    python modules/net/arpwatch.py --save          # (re)write the baseline
    python modules/net/arpwatch.py --watch 30      # poll every 30s, alert on change
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_STATE = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "arp_baseline.json"))
_MAC = re.compile(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})")


def read_table() -> dict[str, dict]:
    """Return {ip: {mac, iface, state}} from `ip neigh show`."""
    if shutil.which("ip") is None:
        raise FileNotFoundError("ip")
    proc = subprocess.run(["ip", "neigh", "show"], capture_output=True,
                          text=True, timeout=10)
    table: dict[str, dict] = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if not parts or parts[0] == "":
            continue
        ip = parts[0]
        mac_m = _MAC.search(line)
        iface = parts[parts.index("dev") + 1] if "dev" in parts else None
        state = parts[-1] if parts[-1].isupper() else None
        # Skip entries with no resolved MAC (FAILED/INCOMPLETE) for spoof logic,
        # but still record state.
        table[ip] = {"mac": mac_m.group(1).lower() if mac_m else None,
                     "iface": iface, "state": state}
    return table


def diff(old: dict, new: dict) -> list[tuple[str, str, str]]:
    """Yield (kind, ip, detail)."""
    events = []
    for ip, cur in new.items():
        if cur["mac"] is None:
            continue
        prev = old.get(ip)
        if prev is None or prev.get("mac") is None:
            events.append(("NEW", ip, f"{cur['mac']} on {cur['iface']}"))
        elif prev["mac"] != cur["mac"]:
            events.append(("CHANGED", ip,
                           f"{prev['mac']} -> {cur['mac']}  (possible spoof)"))
    for ip, prev in old.items():
        if prev.get("mac") and ip not in new:
            events.append(("GONE", ip, prev["mac"]))
    return events


def _load_baseline() -> dict:
    try:
        with open(_STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_baseline(table: dict) -> None:
    os.makedirs(os.path.dirname(_STATE), exist_ok=True)
    with open(_STATE, "w", encoding="utf-8") as fh:
        json.dump(table, fh, indent=2)


def _print_table(table: dict) -> None:
    for ip in sorted(table, key=lambda x: tuple(int(o) for o in x.split(".")
                     if o.isdigit()) or (x,)):
        e = table[ip]
        print(f"{ip:<16} {e['mac'] or '(unresolved)':<18} "
              f"{e['state'] or '':<12} {e['iface'] or ''}")


def _print_events(events) -> None:
    for kind, ip, detail in events:
        marker = "!!" if kind == "CHANGED" else "->"
        print(f"{marker} {kind:<8} {ip:<16} {detail}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net arpwatch",
                                 description="ARP snapshot + spoof detection.")
    ap.add_argument("--save", action="store_true", help="write current table as baseline")
    ap.add_argument("--watch", type=float, metavar="SECONDS",
                    help="poll continuously and alert on changes")
    args = ap.parse_args(argv)

    try:
        if args.watch:
            prev = read_table()
            _print_table(prev)
            print(f"; watching every {args.watch:g}s — Ctrl-C to stop", file=sys.stderr)
            while True:
                time.sleep(args.watch)
                cur = read_table()
                events = diff(prev, cur)
                if events:
                    print(f"; {time.strftime('%H:%M:%S')}", file=sys.stderr)
                    _print_events(events)
                prev = cur

        table = read_table()
        if args.save:
            _save_baseline(table)
            print(f"baseline saved: {len(table)} entries -> {_STATE}")
            return 0

        baseline = _load_baseline()
        _print_table(table)
        if baseline:
            events = diff(baseline, table)
            if events:
                print("; changes vs baseline:", file=sys.stderr)
                _print_events(events)
                return 1
        else:
            print("; no baseline yet — run with --save to create one",
                  file=sys.stderr)
        return 0
    except FileNotFoundError:
        print("[arpwatch] 'ip' not found — `pkg install iproute2`", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n; stopped", file=sys.stderr)
        return 0
    except subprocess.TimeoutExpired:
        print("[arpwatch] 'ip neigh' timed out", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
