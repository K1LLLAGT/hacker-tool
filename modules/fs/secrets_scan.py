"""
fs/secrets_scan.py — regex scan for committed secrets (stdlib re).

Finds accidentally-stored credentials in a tree: cloud keys, tokens, private
keys, JWTs, and generic secret assignments. Matches are REDACTED by default so
the scan output/logs don't themselves leak the secret. Defensive hygiene tool
(same job as git-secrets / gitleaks).

    python modules/fs/secrets_scan.py .
    python modules/fs/secrets_scan.py . --show          # reveal full match
    python modules/fs/secrets_scan.py . --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

DEFAULT_SKIP_DIRS = {".git", "__pycache__", ".venv", "venvs", "node_modules",
                     ".audit-backups", "reports"}
_MAX_BYTES = 2 * 1024 * 1024   # skip files bigger than 2 MB

# name -> compiled pattern. Ordered most-specific first.
PATTERNS = {
    "aws_access_key_id":  re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key_block":  re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "github_token":       re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36}\b"),
    "github_pat_fine":    re.compile(r"\bgithub_pat_[0-9A-Za-z_]{22,}\b"),
    "slack_token":        re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    "google_api_key":     re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "jwt":                re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "bearer_token":       re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]{20,}"),
    "generic_secret":     re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password|passwd|pwd|access[_-]?key)"
        r"\s*[:=]\s*[\"']?([^\s\"']{8,})"),
}


def _redact(s: str) -> str:
    s = s.strip()
    if len(s) <= 8:
        return s[0] + "*" * (len(s) - 1) if s else s
    return f"{s[:4]}{'*' * (len(s) - 6)}{s[-2:]}"


def _is_text(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\x00" not in fh.read(4096)
    except OSError:
        return False


def scan_file(path: str, show: bool = False) -> list[dict]:
    hits: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if len(line) > 4000:      # skip minified/huge lines
                    continue
                for name, pat in PATTERNS.items():
                    m = pat.search(line)
                    if not m:
                        continue
                    raw = m.group(m.lastindex or 0)
                    hits.append({
                        "file": path, "line": lineno, "rule": name,
                        "match": raw if show else _redact(raw),
                    })
                    break   # one rule per line is enough to flag it
    except OSError:
        pass
    return hits


def scan_tree(root: str, show: bool = False,
              skip_dirs: set[str] | None = None) -> list[dict]:
    skip = skip_dirs if skip_dirs is not None else DEFAULT_SKIP_DIRS
    findings: list[dict] = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip]
        for name in fns:
            full = os.path.join(dp, name)
            try:
                if os.path.islink(full) or os.path.getsize(full) > _MAX_BYTES:
                    continue
            except OSError:
                continue
            if _is_text(full):
                findings.extend(scan_file(full, show))
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fs secrets-scan",
                                 description="Scan for committed secrets.")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--show", action="store_true", help="reveal full matches (careful)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip", action="append", default=[], help="extra dir name to skip")
    args = ap.parse_args(argv)

    skip = DEFAULT_SKIP_DIRS | set(args.skip)
    findings = scan_tree(args.root, args.show, skip)

    if args.json:
        print(json.dumps(findings, indent=2))
        return 1 if findings else 0

    if not findings:
        print("no secrets found")
        return 0
    for f in findings:
        rel = os.path.relpath(f["file"], args.root)
        print(f"{rel}:{f['line']}  [{f['rule']}]  {f['match']}")
    print(f"; {len(findings)} potential secret(s)"
          + ("" if args.show else " — matches redacted; --show to reveal"),
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
