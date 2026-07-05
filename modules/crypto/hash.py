"""
crypto/hash.py — hash a string, file, or stdin (stdlib hashlib).

    python modules/crypto/hash.py --text "hello"
    python modules/crypto/hash.py --file report.pdf --algo sha512
    echo -n data | python modules/crypto/hash.py --algo sha256
    python modules/crypto/hash.py --file x --all
"""
from __future__ import annotations

import argparse
import hashlib
import sys

COMMON = ["md5", "sha1", "sha256", "sha512"]


def hash_bytes(data: bytes, algo: str) -> str:
    h = hashlib.new(algo)
    h.update(data)
    return h.hexdigest()


def hash_file(path: str, algo: str, chunk: int = 1 << 16) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="crypto hash", description="Hash text/file/stdin.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", "-t", help="hash this string (utf-8)")
    src.add_argument("--file", "-f", help="hash this file")
    ap.add_argument("--algo", "-a", default="sha256", help="hashlib algorithm")
    ap.add_argument("--all", action="store_true", help="print md5/sha1/sha256/sha512")
    args = ap.parse_args(argv)

    algos = COMMON if args.all else [args.algo]
    for a in algos:
        if a not in hashlib.algorithms_available:
            print(f"[hash] unknown algo {a!r}; try {', '.join(sorted(hashlib.algorithms_guaranteed))}",
                  file=sys.stderr)
            return 2

    try:
        if args.file:
            for a in algos:
                print(f"{a:<8} {hash_file(args.file, a)}")
        else:
            data = args.text.encode("utf-8") if args.text is not None \
                else sys.stdin.buffer.read()
            for a in algos:
                print(f"{a:<8} {hash_bytes(data, a)}")
    except OSError as e:
        print(f"[hash] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
