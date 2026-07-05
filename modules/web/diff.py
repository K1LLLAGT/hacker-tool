"""
web/diff.py — detect page changes by diffing response bodies (stdlib).

Two modes:
  * one URL   -> fetch twice (optionally with --delay) to catch dynamic changes
  * two URLs  -> compare them (e.g. staging vs prod)

    python modules/web/diff.py https://example.com
    python modules/web/diff.py https://example.com --delay 5
    python modules/web/diff.py https://staging.site https://www.site
"""
from __future__ import annotations

import argparse
import difflib
import sys
import time
import urllib.error
import urllib.request

UA = "hacker-tool/web-diff"


def _normalize(url: str) -> str:
    return url if "://" in url else "https://" + url


def fetch_text(url: str, timeout: float = 12.0) -> list[str]:
    req = urllib.request.Request(_normalize(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "replace").splitlines(keepends=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web diff", description="Diff web page bodies.")
    ap.add_argument("url_a")
    ap.add_argument("url_b", nargs="?", help="second URL; omit to fetch url_a twice")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="seconds between the two fetches (same-URL mode)")
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args(argv)

    try:
        a = fetch_text(args.url_a, args.timeout)
        if args.url_b:
            b = fetch_text(args.url_b, args.timeout)
            label_a, label_b = args.url_a, args.url_b
        else:
            if args.delay:
                time.sleep(args.delay)
            b = fetch_text(args.url_a, args.timeout)
            label_a, label_b = f"{args.url_a}#1", f"{args.url_a}#2"
    except (urllib.error.URLError, OSError) as e:
        print(f"[diff] {e}", file=sys.stderr)
        return 2

    delta = list(difflib.unified_diff(a, b, fromfile=label_a, tofile=label_b))
    if not delta:
        print("identical (no body changes)")
        return 0
    sys.stdout.writelines(delta)
    added = sum(1 for l in delta if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in delta if l.startswith("-") and not l.startswith("---"))
    print(f"\n; changed: +{added} / -{removed} lines", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
