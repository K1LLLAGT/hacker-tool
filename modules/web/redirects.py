"""
web/redirects.py — follow and log every HTTP redirect hop (stdlib urllib).

Disables auto-follow and walks the 3xx chain by hand so each hop is visible,
with a cap to catch loops.

    python modules/web/redirects.py http://github.com
    python modules/web/redirects.py example.com --max 15
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "hacker-tool/web-redirects"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None       # returning None makes urllib surface the 3xx itself


def _opener():
    return urllib.request.build_opener(_NoRedirect)


def _normalize(url: str) -> str:
    return url if "://" in url else "http://" + url


def follow(url: str, max_hops: int = 10, timeout: float = 10.0) -> list[dict]:
    opener = _opener()
    hops: list[dict] = []
    current = _normalize(url)
    seen: set[str] = set()
    for _ in range(max_hops):
        req = urllib.request.Request(current, method="GET",
                                     headers={"User-Agent": UA})
        try:
            resp = opener.open(req, timeout=timeout)
            code, loc = resp.status, None
            resp.close()
        except urllib.error.HTTPError as e:
            code = e.code
            loc = e.headers.get("Location") if e.headers else None
        hops.append({"url": current, "status": code, "location": loc})
        if not (300 <= code < 400) or not loc:
            break
        nxt = urllib.parse.urljoin(current, loc)
        if nxt in seen:
            hops.append({"url": nxt, "status": None, "location": "LOOP DETECTED"})
            break
        seen.add(nxt)
        current = nxt
    return hops


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web redirects", description="Trace redirect chain.")
    ap.add_argument("url")
    ap.add_argument("--max", type=int, default=10, help="max hops before giving up")
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args(argv)

    try:
        hops = follow(args.url, args.max, args.timeout)
    except (urllib.error.URLError, OSError) as e:
        print(f"[redirects] {e}", file=sys.stderr)
        return 2

    for i, h in enumerate(hops):
        arrow = f" -> {h['location']}" if h["location"] and 300 <= (h["status"] or 0) < 400 else ""
        print(f"{i}. {h['status']}  {h['url']}{arrow}")
    final = hops[-1]
    print(f"\nfinal: {final['url']} (HTTP {final['status']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
