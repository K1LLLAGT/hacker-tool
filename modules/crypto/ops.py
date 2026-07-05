"""
modules/crypto/ops.py — local cryptographic utilities.

Offline-only. No network calls. Stdlib only.
Subcommands: hash, encode, decode, entropy, compare
"""
import base64
from collections import Counter
import hashlib
import math
from pathlib import Path

SUPPORTED_ALGOS = ("sha256", "sha1", "md5", "sha512", "sha224", "sha384")


def _read_bytes(file: str = None, text: str = None) -> bytes:
    if file:
        return Path(file).expanduser().read_bytes()
    if text is not None:
        return text.encode()
    raise ValueError("Provide --file or --text")


def hash_data(file: str = None, text: str = None, algo: str = "sha256") -> dict:
    """Hash a file or text string with the given algorithm."""
    if algo not in SUPPORTED_ALGOS:
        raise ValueError(f"Unsupported algo '{algo}'. Choose: {', '.join(SUPPORTED_ALGOS)}")
    data = _read_bytes(file, text)
    digest = hashlib.new(algo, data).hexdigest()
    return {
        "source": file or "<text>",
        "algo": algo,
        "digest": digest,
        "bytes": len(data),
    }


def encode_b64(file: str = None, text: str = None, url_safe: bool = False) -> dict:
    """Base64-encode a file or text string."""
    data = _read_bytes(file, text)
    if url_safe:
        result = base64.urlsafe_b64encode(data).decode()
        enc = "base64url"
    else:
        result = base64.b64encode(data).decode()
        enc = "base64"
    return {"source": file or "<text>", "encoding": enc, "result": result}


def decode_b64(text: str, url_safe: bool = False) -> dict:
    """Base64-decode a string, printing as UTF-8 (lossy)."""
    try:
        if url_safe:
            raw = base64.urlsafe_b64decode(text.strip() + "==")
        else:
            raw = base64.b64decode(text.strip() + "==")
        decoded = raw.decode(errors="replace")
    except Exception as e:
        raise ValueError(f"base64 decode failed: {e}")
    return {"encoding": "base64url" if url_safe else "base64",
            "bytes": len(raw), "result": decoded}


def shannon_entropy(file: str) -> dict:
    """Shannon entropy of a file — high entropy signals encryption or packing."""
    data = Path(file).expanduser().read_bytes()
    if not data:
        return {"file": file, "entropy": 0.0, "size_bytes": 0, "verdict": "empty"}
    counts = Counter(data)
    total = len(data)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    if entropy > 7.5:
        verdict = "likely encrypted or compressed"
    elif entropy > 6.0:
        verdict = "high — possibly packed binary"
    else:
        verdict = "normal"
    return {
        "file": file,
        "entropy": round(entropy, 4),
        "max_entropy": 8.0,
        "size_bytes": total,
        "verdict": verdict,
    }


def compare_hashes(hash_a: str, hash_b: str) -> dict:
    """Constant-time comparison of two hex digest strings."""
    import hmac
    match = hmac.compare_digest(hash_a.strip().lower(), hash_b.strip().lower())
    return {"hash_a": hash_a.strip(), "hash_b": hash_b.strip(), "match": match}
