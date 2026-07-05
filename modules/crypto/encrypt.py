"""
crypto/encrypt.py — file encryption, stdlib only.

Two modes:

  stream  (default)  A real password-based authenticated cipher built from
                     stdlib primitives: scrypt KDF -> HMAC-SHA256 keystream in
                     counter mode -> encrypt-then-MAC (HMAC-SHA256). Tamper is
                     detected on decrypt. Use this for anything you actually
                     want protected.

  xor                Repeating-key XOR. This is OBFUSCATION, NOT ENCRYPTION —
                     trivially breakable. Included only for compatibility with
                     the existing core/secrets.py engine and for CTF/testing.

    python modules/crypto/encrypt.py enc secret.txt secret.enc            # prompts for password
    python modules/crypto/encrypt.py dec secret.enc secret.out
    python modules/crypto/encrypt.py enc a.bin a.xor --mode xor --keystring hunter2
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import os
import secrets
import struct
import sys

MAGIC = b"HTS1"          # hacker-tool stream v1
_SALT = 16
_NONCE = 16
_TAG = 32
_BLOCK = 32              # HMAC-SHA256 output size


def _derive(password: bytes, salt: bytes) -> tuple[bytes, bytes]:
    try:
        dk = hashlib.scrypt(password, salt=salt, n=1 << 14, r=8, p=1, dklen=64)
    except (ValueError, MemoryError):        # low-memory fallback
        dk = hashlib.pbkdf2_hmac("sha256", password, salt, 200_000, dklen=64)
    return dk[:32], dk[32:]                  # (enc_key, mac_key)


def _keystream(enc_key: bytes, nonce: bytes, nbytes: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < nbytes:
        block = hmac.new(enc_key, nonce + struct.pack(">Q", counter),
                         hashlib.sha256).digest()
        out += block
        counter += 1
    return bytes(out[:nbytes])


def _xor(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("empty key")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_stream(plaintext: bytes, password: bytes) -> bytes:
    salt, nonce = secrets.token_bytes(_SALT), secrets.token_bytes(_NONCE)
    enc_key, mac_key = _derive(password, salt)
    ct = bytes(a ^ b for a, b in zip(plaintext, _keystream(enc_key, nonce, len(plaintext))))
    header = MAGIC + salt + nonce
    tag = hmac.new(mac_key, header + ct, hashlib.sha256).digest()
    return header + ct + tag


def decrypt_stream(blob: bytes, password: bytes) -> bytes:
    if blob[:4] != MAGIC:
        raise ValueError("not a stream-mode file (bad magic)")
    off = 4
    salt = blob[off:off + _SALT]; off += _SALT
    nonce = blob[off:off + _NONCE]; off += _NONCE
    ct = blob[off:-_TAG]
    tag = blob[-_TAG:]
    enc_key, mac_key = _derive(password, salt)
    expect = hmac.new(mac_key, blob[:4 + _SALT + _NONCE] + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expect):
        raise ValueError("authentication FAILED — wrong password or tampered file")
    return bytes(a ^ b for a, b in zip(ct, _keystream(enc_key, nonce, len(ct))))


def _get_key_bytes(args) -> bytes:
    if args.keystring is not None:
        return args.keystring.encode("utf-8")
    if args.key:
        with open(args.key, "rb") as fh:
            return fh.read()
    pw = os.environ.get("HT_CRYPTO_PASSWORD")
    if pw:
        return pw.encode("utf-8")
    return getpass.getpass("password: ").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="crypto encrypt", description="Encrypt/decrypt a file.")
    ap.add_argument("action", choices=["enc", "dec"])
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--mode", choices=["stream", "xor"], default="stream")
    ap.add_argument("--key", help="key FILE (xor mode)")
    ap.add_argument("--keystring", help="key/password as a string")
    args = ap.parse_args(argv)

    if args.mode == "xor":
        print("[encrypt] WARNING: xor mode is obfuscation, NOT secure encryption.",
              file=sys.stderr)

    try:
        with open(args.infile, "rb") as fh:
            data = fh.read()
        key = _get_key_bytes(args)
        if args.mode == "xor":
            result = _xor(data, key)
        elif args.action == "enc":
            result = encrypt_stream(data, key)
        else:
            result = decrypt_stream(data, key)
        with open(args.outfile, "wb") as fh:
            fh.write(result)
    except ValueError as e:
        print(f"[encrypt] {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[encrypt] {e}", file=sys.stderr)
        return 2

    verb = "encrypted" if args.action == "enc" else "decrypted"
    print(f"{verb} ({args.mode}) {args.infile} -> {args.outfile} ({len(result)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
