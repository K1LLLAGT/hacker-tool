"""
crypto/verify.py — verify a file against a known-good hash (stdlib hashlib).

Provide the expected hash directly, a coreutils-style ``.sha256`` sidecar, or a
checksums file listing many entries. Algorithm is inferred from digest length
unless given. Uses a constant-time comparison.

    python modules/crypto/verify.py file.iso --sha256 ab12...ef
    python modules/crypto/verify.py file.iso --sidecar file.iso.sha256
    python modules/crypto/verify.py --checksums SHA256SUMS        # verify all
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sys

_BY_LEN = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}


def _hash_file(path: str, algo: str, chunk: int = 1 << 16) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _infer_algo(digest: str, override: str | None) -> str:
    if override:
        return override
    algo = _BY_LEN.get(len(digest.strip()))
    if not algo:
        raise ValueError(f"can't infer algo from {len(digest)}-char digest; use --algo")
    return algo


def verify_one(path: str, expected: str, algo: str | None = None) -> bool:
    expected = expected.strip().lower()
    algo = _infer_algo(expected, algo)
    actual = _hash_file(path, algo).lower()
    return hmac.compare_digest(actual, expected)


def _parse_checksums(text: str) -> list[tuple[str, str]]:
    """Parse '<hash>  <filename>' lines (coreutils format)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            digest, name = parts
            out.append((digest, name.lstrip("*")))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="crypto verify", description="Verify file checksums.")
    ap.add_argument("file", nargs="?", help="file to verify (not needed with --checksums)")
    ap.add_argument("--sha256")
    ap.add_argument("--sha1")
    ap.add_argument("--sha512")
    ap.add_argument("--md5")
    ap.add_argument("--hash", help="expected digest (algo inferred from length)")
    ap.add_argument("--algo", help="force algorithm")
    ap.add_argument("--sidecar", help="read expected digest from this sidecar file")
    ap.add_argument("--checksums", help="verify every entry in a SHA256SUMS-style file")
    args = ap.parse_args(argv)

    try:
        if args.checksums:
            base = os.path.dirname(os.path.abspath(args.checksums))
            with open(args.checksums, encoding="utf-8") as fh:
                entries = _parse_checksums(fh.read())
            if not entries:
                print("[verify] no entries parsed", file=sys.stderr)
                return 2
            bad = 0
            for digest, name in entries:
                target = name if os.path.isabs(name) else os.path.join(base, name)
                if not os.path.exists(target):
                    print(f"MISSING  {name}")
                    bad += 1
                    continue
                ok = verify_one(target, digest, args.algo)
                print(f"{'OK      ' if ok else 'FAIL    '} {name}")
                bad += 0 if ok else 1
            print(f"; {len(entries) - bad}/{len(entries)} verified", file=sys.stderr)
            return 1 if bad else 0

        if not args.file:
            ap.error("provide a file (or use --checksums)")

        expected = (args.sha256 or args.sha1 or args.sha512 or args.md5 or args.hash)
        algo = args.algo
        if args.sha256:
            algo = algo or "sha256"
        elif args.sha1:
            algo = algo or "sha1"
        elif args.sha512:
            algo = algo or "sha512"
        elif args.md5:
            algo = algo or "md5"
        if args.sidecar:
            with open(args.sidecar, encoding="utf-8") as fh:
                first = fh.read().split()
            expected = first[0] if first else None
        if not expected:
            print("[verify] no expected hash given (--sha256/--hash/--sidecar)",
                  file=sys.stderr)
            return 2

        ok = verify_one(args.file, expected, algo)
        print(f"{'OK' if ok else 'FAIL'}  {args.file}")
        if not ok:
            print(f"  expected {expected.strip().lower()}", file=sys.stderr)
            print(f"  actual   {_hash_file(args.file, _infer_algo(expected, algo))}",
                  file=sys.stderr)
        return 0 if ok else 1
    except (OSError, ValueError) as e:
        print(f"[verify] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
