"""
net/dns.py — pure-stdlib DNS client.

Forward (A, AAAA, MX, TXT, NS, CNAME) and reverse (PTR) lookups built on raw
UDP wire-format queries. No dnspython, no external binaries. stdlib only.

    python modules/net/dns.py example.com                 # A record
    python modules/net/dns.py example.com --type MX
    python modules/net/dns.py example.com --type ANY_COMMON
    python modules/net/dns.py 1.1.1.1 --reverse
    python modules/net/dns.py example.com --server 8.8.8.8
"""
from __future__ import annotations

import argparse
import random
import socket
import struct
import sys

QTYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12,
          "MX": 15, "TXT": 16, "AAAA": 28}
_TYPE_BY_NUM = {v: k for k, v in QTYPES.items()}
DEFAULT_SERVER = "1.1.1.1"


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        try:
            b = label.encode("ascii")
        except UnicodeEncodeError:
            b = label.encode("idna")
        if len(b) > 63:
            raise ValueError(f"label too long: {label!r}")
        out.append(len(b))
        out += b
    out.append(0)
    return bytes(out)


def _read_name(msg: bytes, off: int) -> tuple[str, int]:
    """Decode a (possibly compressed) name; return (name, next_offset)."""
    labels: list[str] = []
    jumped = False
    next_off = off
    while True:
        length = msg[off]
        if length & 0xC0 == 0xC0:                       # compression pointer
            pointer = ((length & 0x3F) << 8) | msg[off + 1]
            if not jumped:
                next_off = off + 2
            off = pointer
            jumped = True
            continue
        off += 1
        if length == 0:
            break
        labels.append(msg[off:off + length].decode("utf-8", "replace"))
        off += length
    if not jumped:
        next_off = off
    return ".".join(labels), next_off


def _build_query(qname: str, qtype: int) -> tuple[bytes, int]:
    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 1)   # RD set, 1 additional
    question = _encode_name(qname) + struct.pack(">HH", qtype, 1)
    # EDNS0 OPT pseudo-record advertising a 4096-byte UDP buffer (avoids TC).
    opt = b"\x00" + struct.pack(">HHIH", 41, 4096, 0, 0)
    return header + question + opt, tid


def _parse_rdata(rtype: int, msg: bytes, off: int, rdlen: int) -> str:
    end = off + rdlen
    if rtype == 1:                                      # A
        return socket.inet_ntop(socket.AF_INET, msg[off:off + 4])
    if rtype == 28:                                     # AAAA
        return socket.inet_ntop(socket.AF_INET6, msg[off:off + 16])
    if rtype in (2, 5, 12):                             # NS / CNAME / PTR
        name, _ = _read_name(msg, off)
        return name
    if rtype == 15:                                     # MX
        pref = struct.unpack(">H", msg[off:off + 2])[0]
        name, _ = _read_name(msg, off + 2)
        return f"{pref} {name}"
    if rtype == 16:                                     # TXT (1+ char-strings)
        parts, p = [], off
        while p < end:
            slen = msg[p]
            parts.append(msg[p + 1:p + 1 + slen].decode("utf-8", "replace"))
            p += 1 + slen
        return '"' + "".join(parts) + '"'
    return msg[off:end].hex()


def query(qname: str, qtype: str = "A", server: str = DEFAULT_SERVER,
          timeout: float = 3.0) -> list[dict]:
    """Return a list of {name,type,ttl,data} answer records."""
    qtype = qtype.upper()
    if qtype not in QTYPES:
        raise ValueError(f"unknown type {qtype}; try {', '.join(QTYPES)}")
    pkt, tid = _build_query(qname, QTYPES[qtype])
    fam = socket.AF_INET6 if ":" in server else socket.AF_INET
    with socket.socket(fam, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(pkt, (server, 53))
        data, _ = s.recvfrom(4096)

    rid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    if rid != tid:
        raise RuntimeError("transaction id mismatch")
    rcode = flags & 0x0F
    if rcode == 3:
        return []                                       # NXDOMAIN → empty
    if rcode != 0:
        raise RuntimeError(f"server returned rcode {rcode}")

    off = 12
    for _ in range(qd):                                 # skip question(s)
        _, off = _read_name(data, off)
        off += 4
    answers = []
    for _ in range(an):
        name, off = _read_name(data, off)
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", data[off:off + 10])
        off += 10
        answers.append({
            "name": name,
            "type": _TYPE_BY_NUM.get(rtype, str(rtype)),
            "ttl": ttl,
            "data": _parse_rdata(rtype, data, off, rdlen),
        })
        off += rdlen
    return answers


def _reverse_name(ip: str) -> str:
    if ":" in ip:
        full = socket.inet_pton(socket.AF_INET6, ip).hex()
        return ".".join(reversed(full)) + ".ip6.arpa"
    octets = ip.split(".")
    return ".".join(reversed(octets)) + ".in-addr.arpa"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="net dns", description="Pure-stdlib DNS lookups.")
    ap.add_argument("target", help="hostname (forward) or IP (with --reverse)")
    ap.add_argument("--type", "-t", default="A",
                    help="A, AAAA, MX, TXT, NS, CNAME, SOA, or ANY_COMMON")
    ap.add_argument("--reverse", "-x", action="store_true", help="PTR lookup for an IP")
    ap.add_argument("--server", "-s", default=DEFAULT_SERVER, help="resolver IP")
    ap.add_argument("--timeout", type=float, default=3.0)
    args = ap.parse_args(argv)

    try:
        if args.reverse:
            recs = query(_reverse_name(args.target), "PTR", args.server, args.timeout)
            plan = [("PTR", recs)]
        elif args.type.upper() == "ANY_COMMON":
            plan = [(t, query(args.target, t, args.server, args.timeout))
                    for t in ("A", "AAAA", "MX", "TXT", "NS")]
        else:
            plan = [(args.type.upper(),
                     query(args.target, args.type, args.server, args.timeout))]
    except (socket.gaierror, socket.timeout, OSError) as e:
        print(f"[dns] network error: {e}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as e:
        print(f"[dns] {e}", file=sys.stderr)
        return 2

    any_hit = False
    for label, recs in plan:
        for r in recs:
            any_hit = True
            print(f"{r['name']:<40} {r['ttl']:>7}  {r['type']:<6} {r['data']}")
        if not recs:
            print(f"; no {label} records", file=sys.stderr)
    return 0 if any_hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
