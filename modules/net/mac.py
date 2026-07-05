"""
net/mac.py — MAC address -> vendor via bundled OUI table (stdlib json).

Offline lookup against data/oui.json. Handles any separator style and MAC-48
or EUI-64. Also flags locally-administered / multicast addresses.

    python modules/net/mac.py 2C:CF:67:C8:96:9B
    python modules/net/mac.py 2ccf67c8969b
    python modules/net/mac.py --file addresses.txt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "oui.json"))
_HEX = re.compile(r"[0-9A-Fa-f]")


def _normalize(mac: str) -> str:
    return "".join(_HEX.findall(mac)).upper()


def load_db(path: str = _DEFAULT_DB) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    # Normalize keys so separators/case in the file never matter.
    return {_normalize(k): v for k, v in raw.items() if not k.startswith("_")}


def lookup(mac: str, db: dict[str, str]) -> dict:
    hexs = _normalize(mac)
    out: dict = {"input": mac, "normalized": hexs, "vendor": None,
                 "local": None, "multicast": None, "valid": False}
    if len(hexs) < 6:
        return out
    out["valid"] = True
    first_octet = int(hexs[0:2], 16)
    out["multicast"] = bool(first_octet & 0x01)
    out["local"] = bool(first_octet & 0x02)
    out["vendor"] = db.get(hexs[0:6])
    if out["vendor"] is None and out["local"]:
        out["vendor"] = "(locally-administered — not a real OUI)"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net mac", description="MAC -> vendor lookup.")
    ap.add_argument("mac", nargs="*", help="one or more MAC addresses")
    ap.add_argument("--file", "-f", help="read MACs one per line from a file")
    ap.add_argument("--db", default=_DEFAULT_DB, help="path to oui.json")
    args = ap.parse_args(argv)

    try:
        db = load_db(args.db)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[mac] cannot load OUI db {args.db}: {e}", file=sys.stderr)
        return 2

    macs = list(args.mac)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                macs += [ln.strip() for ln in fh if ln.strip()]
        except OSError as e:
            print(f"[mac] {e}", file=sys.stderr)
            return 2
    if not macs:
        ap.error("provide a MAC address or --file")

    hits = 0
    for m in macs:
        r = lookup(m, db)
        if not r["valid"]:
            print(f"{m:<20} invalid")
            continue
        vendor = r["vendor"] or "unknown"
        if r["vendor"]:
            hits += 1
        flags = " ".join(f for f, on in
                         (("multicast", r["multicast"]), ("local", r["local"])) if on)
        print(f"{m:<20} {vendor}" + (f"   [{flags}]" if flags else ""))
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
