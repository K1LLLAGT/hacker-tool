"""
web/fingerprint.py — identify server/CMS/framework from headers + HTML (stdlib).

Signature-based detection across response headers, cookies, and body markers.
Best-effort, not exhaustive — flags what it can see, doesn't guess wildly.

    python modules/web/fingerprint.py https://example.com
    python modules/web/fingerprint.py example.com --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

UA = "hacker-tool/web-fingerprint"

# (label, where, compiled-regex). where in {"header:<name>", "cookie", "body"}
SIGNATURES = [
    ("WordPress", "body", re.compile(r"/wp-(?:content|includes|json)/", re.I)),
    ("WordPress", "header:link", re.compile(r"wp-json", re.I)),
    ("Drupal", "header:x-generator", re.compile(r"Drupal", re.I)),
    ("Drupal", "body", re.compile(r"/sites/(?:default|all)/", re.I)),
    ("Joomla", "body", re.compile(r"/media/jui/|Joomla", re.I)),
    ("Shopify", "header:x-shopid", re.compile(r".+")),
    ("Shopify", "body", re.compile(r"cdn\.shopify\.com", re.I)),
    ("Django", "cookie", re.compile(r"\bcsrftoken=|\bsessionid=", re.I)),
    ("Rails", "cookie", re.compile(r"_session_id=", re.I)),
    ("Laravel", "cookie", re.compile(r"laravel_session=", re.I)),
    ("Express", "header:x-powered-by", re.compile(r"Express", re.I)),
    ("PHP", "header:x-powered-by", re.compile(r"PHP", re.I)),
    ("ASP.NET", "header:x-powered-by", re.compile(r"ASP\.NET", re.I)),
    ("Next.js", "header:x-powered-by", re.compile(r"Next\.js", re.I)),
    ("Cloudflare", "header:server", re.compile(r"cloudflare", re.I)),
    ("nginx", "header:server", re.compile(r"nginx", re.I)),
    ("Apache", "header:server", re.compile(r"Apache", re.I)),
    ("Google Analytics", "body", re.compile(r"gtag\(|googletagmanager\.com", re.I)),
    ("jQuery", "body", re.compile(r"jquery(?:-|\.)\d", re.I)),
    ("React", "body", re.compile(r"__NEXT_DATA__|data-reactroot|react(?:-dom)?\.", re.I)),
]


def _normalize(url: str) -> str:
    return url if "://" in url else "https://" + url


def fetch(url: str, timeout: float = 12.0) -> dict:
    req = urllib.request.Request(_normalize(url), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(300_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status, final = resp.status, resp.geturl()
    except urllib.error.HTTPError as e:
        body = e.read(300_000) if hasattr(e, "read") else b""
        headers = {k.lower(): v for k, v in (e.headers or {}).items()}
        charset, status, final = "utf-8", e.code, url
    return {"status": status, "url": final, "headers": headers,
            "cookie": headers.get("set-cookie", ""),
            "body": body.decode(charset, "replace")}


def fingerprint(data: dict) -> list[str]:
    found: list[str] = []
    for label, where, pat in SIGNATURES:
        if where == "body":
            hay = data["body"]
        elif where == "cookie":
            hay = data["cookie"]
        elif where.startswith("header:"):
            hay = data["headers"].get(where.split(":", 1)[1], "")
        else:
            hay = ""
        if hay and pat.search(hay) and label not in found:
            found.append(label)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web fingerprint", description="Detect web stack.")
    ap.add_argument("url")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        data = fetch(args.url, args.timeout)
    except (urllib.error.URLError, OSError) as e:
        print(f"[fingerprint] {e}", file=sys.stderr)
        return 2

    tech = fingerprint(data)
    server = data["headers"].get("server", "?")
    powered = data["headers"].get("x-powered-by")
    if args.json:
        print(json.dumps({"url": data["url"], "status": data["status"],
                          "server": server, "x_powered_by": powered,
                          "detected": tech}, indent=2))
        return 0
    print(f"{data['url']}  (HTTP {data['status']})")
    print(f"server        {server}")
    if powered:
        print(f"x-powered-by  {powered}")
    print(f"detected      {', '.join(tech) if tech else '(no signatures matched)'}")
    return 0 if tech or server != "?" else 1


if __name__ == "__main__":
    raise SystemExit(main())
