"""
net/wifi.py — WiFi scan & connection info via termux-api (stdlib json/subprocess).

Wraps `termux-wifi-scaninfo` (nearby APs) and `termux-wifi-connectioninfo`
(current link). Requires the Termux:API app + `pkg install termux-api`.

    python modules/net/wifi.py            # current connection
    python modules/net/wifi.py --scan     # nearby access points
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


def _run_json(cmd: list[str], timeout: float = 15.0):
    if shutil.which(cmd[0]) is None:
        raise FileNotFoundError(cmd[0])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"{cmd[0]} exited {proc.returncode}")
    return json.loads(proc.stdout or "null")


def connection() -> dict:
    return _run_json(["termux-wifi-connectioninfo"]) or {}


def scan() -> list[dict]:
    data = _run_json(["termux-wifi-scaninfo"])
    return data if isinstance(data, list) else []


def _secpretty(caps: str) -> str:
    caps = (caps or "").upper()
    for tag in ("WPA3", "WPA2", "WPA", "WEP"):
        if tag in caps:
            return tag
    return "OPEN" if caps in ("", "[ESS]") else caps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net wifi", description="WiFi info via termux-api.")
    ap.add_argument("--scan", action="store_true", help="list nearby APs")
    ap.add_argument("--json", action="store_true", help="raw JSON passthrough")
    args = ap.parse_args(argv)

    try:
        if args.scan:
            aps = scan()
            if args.json:
                print(json.dumps(aps, indent=2))
                return 0
            aps.sort(key=lambda a: a.get("rssi", -999), reverse=True)
            print(f"{'SSID':<28} {'BSSID':<18} {'RSSI':>5} {'CH':>4}  SEC")
            for a in aps:
                ssid = a.get("ssid") or "(hidden)"
                print(f"{ssid[:28]:<28} {a.get('bssid',''):<18} "
                      f"{a.get('rssi',''):>5} {a.get('channel',''):>4}  "
                      f"{_secpretty(a.get('capabilities',''))}")
            return 0 if aps else 1
        info = connection()
        if args.json:
            print(json.dumps(info, indent=2))
            return 0
        if not info or info.get("supplicant_state") == "DISCONNECTED":
            print("not connected to WiFi")
            return 1
        for key in ("ssid", "bssid", "ip", "link_speed_mbps", "frequency_mhz", "rssi"):
            if key in info:
                print(f"{key:<18} {info[key]}")
        return 0
    except FileNotFoundError as e:
        print(f"[wifi] '{e}' not found — install Termux:API app and "
              f"`pkg install termux-api`", file=sys.stderr)
        return 2
    except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
        print(f"[wifi] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
