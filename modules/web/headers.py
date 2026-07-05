"""
web/headers.py — HTTP security-header audit (stdlib urllib).

Fetches a URL and grades the response for the headers that matter:
HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy. Online / opt-in — meant for sites you operate.

    python modules/web/headers.py https://example.com
    python modules/web/headers.py example.com --json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

UA = "hacker-tool/web-headers"
CHECK = {
    "Strict-Transport-Security": "HSTS — forces HTTPS",
    "Content-Security-Policy": "CSP — limits resource origins",
    "X-Frame-Options": "clickjacking protection",
    "X-Content-Type-Options": "MIME-sniffing protection (nosniff)",
    "Referrer-Policy": "controls Referer leakage",
    "Permissions-Policy": "restricts browser features",
}


def _normalize(url: str) -> str:
    return url if "://" in url else "https://" + url


def fetch_headers(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(_normalize(url), method="GET",
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": resp.status, "headers": dict(resp.headers),
                    "final_url": resp.geturl()}
    except urllib.error.HTTPError as e:      # 4xx/5xx still carry headers
        return {"status": e.code, "headers": dict(e.headers or {}),
                "final_url": url}


def audit(url: str, timeout: float = 10.0) -> dict:
    data = fetch_headers(url, timeout)
    present = {k: v for k, v in data["headers"].items()}
    lower = {k.lower(): v for k, v in present.items()}
    results = {}
    for name in CHECK:
        results[name] = lower.get(name.lower())
    return {"url": data["final_url"], "status": data["status"], "checks": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web headers", description="Security-header audit.")
    ap.add_argument("url")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        r = audit(args.url, args.timeout)
    except (urllib.error.URLError, OSError) as e:
        print(f"[headers] {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(r, indent=2))
        return 0

    print(f"{r['url']}  (HTTP {r['status']})\n")
    missing = 0
    for name, note in CHECK.items():
        val = r["checks"][name]
        if val:
            shown = val if len(val) <= 60 else val[:57] + "..."
            print(f"  [ok]   {name}: {shown}")
        else:
            missing += 1
            print(f"  [MISS] {name}  — {note}")
    print(f"\n; {len(CHECK) - missing}/{len(CHECK)} present, {missing} missing",
          file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
