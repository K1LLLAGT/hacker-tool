"""
crypto/encode.py — base64 / base32 / hex / url / rot13 encode & decode (stdlib).

    python modules/crypto/encode.py base64 --text "hi there"
    python modules/crypto/encode.py base64 -d --text "aGkgdGhlcmU="
    python modules/crypto/encode.py hex --file blob.bin
    echo -n secret | python modules/crypto/encode.py url
"""
from __future__ import annotations

import argparse
import base64
import codecs
import sys
import urllib.parse

FORMATS = ("base64", "base32", "hex", "url", "rot13")


def _encode(fmt: str, data: bytes) -> str:
    if fmt == "base64":
        return base64.b64encode(data).decode("ascii")
    if fmt == "base32":
        return base64.b32encode(data).decode("ascii")
    if fmt == "hex":
        return data.hex()
    if fmt == "url":
        return urllib.parse.quote_from_bytes(data)
    if fmt == "rot13":
        return codecs.encode(data.decode("utf-8", "replace"), "rot_13")
    raise ValueError(fmt)


def _decode(fmt: str, text: str) -> bytes:
    if fmt == "base64":
        return base64.b64decode(text + "=" * (-len(text) % 4))
    if fmt == "base32":
        return base64.b32decode(text + "=" * (-len(text) % 8))
    if fmt == "hex":
        return bytes.fromhex(text.strip())
    if fmt == "url":
        return urllib.parse.unquote_to_bytes(text)
    if fmt == "rot13":
        return codecs.encode(text, "rot_13").encode("utf-8")
    raise ValueError(fmt)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="crypto encode", description="Encode/decode data.")
    ap.add_argument("format", choices=FORMATS)
    ap.add_argument("--decode", "-d", action="store_true")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", "-t")
    src.add_argument("--file", "-f")
    args = ap.parse_args(argv)

    try:
        if args.decode:
            text = args.text if args.text is not None else (
                open(args.file, encoding="utf-8").read() if args.file
                else sys.stdin.read())
            out = _decode(args.format, text.strip())
            sys.stdout.buffer.write(out)
            if sys.stdout.isatty() and not out.endswith(b"\n"):
                sys.stdout.buffer.write(b"\n")
        else:
            if args.file:
                with open(args.file, "rb") as fh:
                    data = fh.read()
            elif args.text is not None:
                data = args.text.encode("utf-8")
            else:
                data = sys.stdin.buffer.read()
            print(_encode(args.format, data))
    except (ValueError, OSError, base64.binascii.Error) as e:
        print(f"[encode] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
