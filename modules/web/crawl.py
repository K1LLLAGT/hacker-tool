"""
web/crawl.py — map a site by following internal links (stdlib urllib + html.parser).

Breadth-first, same-host only, with depth and page caps plus an optional politeness
delay. Prints the discovered URL tree. For sites you operate.

    python modules/web/crawl.py https://example.com
    python modules/web/crawl.py https://example.com --depth 2 --max 50 --delay 0.3
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser

UA = "hacker-tool/web-crawl"


class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def _normalize(url: str) -> str:
    return url if "://" in url else "https://" + url


def _same_host(a: str, b: str) -> bool:
    return urllib.parse.urlparse(a).netloc.lower() == \
        urllib.parse.urlparse(b).netloc.lower()


def _clean(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path.rstrip("/") or "/",
                                    "", p.query, ""))   # drop fragment


def crawl(start: str, depth: int = 1, max_pages: int = 30,
          delay: float = 0.0, timeout: float = 12.0) -> dict:
    start = _clean(_normalize(start))
    seen = {start}
    edges: dict[str, list[str]] = {}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    while queue and len(edges) < max_pages:
        url, d = queue.popleft()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ctype = resp.headers.get_content_type()
                if ctype != "text/html":
                    edges[url] = []
                    continue
                body = resp.read(500_000).decode(
                    resp.headers.get_content_charset() or "utf-8", "replace")
        except (urllib.error.URLError, OSError):
            edges[url] = ["<unreachable>"]
            continue

        parser = _LinkExtractor()
        parser.feed(body)
        children: list[str] = []
        for href in parser.links:
            nxt = _clean(urllib.parse.urljoin(url, href))
            if not nxt.startswith(("http://", "https://")) or not _same_host(start, nxt):
                continue
            if nxt not in children:
                children.append(nxt)
            if nxt not in seen and d < depth and len(seen) < max_pages:
                seen.add(nxt)
                queue.append((nxt, d + 1))
        edges[url] = children
        if delay:
            time.sleep(delay)
    return {"start": start, "pages": edges, "count": len(edges)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web crawl", description="Map a site's internal links.")
    ap.add_argument("url")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--max", type=int, default=30, dest="max_pages")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds between requests")
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args(argv)

    try:
        r = crawl(args.url, args.depth, args.max_pages, args.delay, args.timeout)
    except (urllib.error.URLError, OSError) as e:
        print(f"[crawl] {e}", file=sys.stderr)
        return 2

    for page in sorted(r["pages"]):
        kids = r["pages"][page]
        print(f"{page}  ({len(kids)} link(s))")
        for k in kids[:8]:
            print(f"    -> {k}")
        if len(kids) > 8:
            print(f"    ... +{len(kids) - 8} more")
    print(f"\n; crawled {r['count']} page(s) from {r['start']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
