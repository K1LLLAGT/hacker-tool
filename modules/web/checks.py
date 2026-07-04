"""
modules/web/checks.py — basic HTTP health/link checks.

Online feature (opt-in). Intended for checking sites you own/operate
(e.g. gwthardwoodfloors.com deployment), not scanning third-party sites.
"""
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def check_url(url: str, timeout: int = 10) -> dict:
    start = time.time()
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed_ms = round((time.time() - start) * 1000, 1)
        return {
            "url": url,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "elapsed_ms": elapsed_ms,
            "final_url": resp.url,
            "content_length": len(resp.content),
        }
    except requests.RequestException as e:
        return {"url": url, "ok": False, "error": str(e)}


def check_links_on_page(url: str, timeout: int = 10, same_domain_only: bool = True) -> dict:
    """Fetches a page and checks all <a href> links for status. Useful for
    catching broken links after a site redesign/deploy."""
    base_domain = urlparse(url).netloc
    resp = requests.get(url, timeout=timeout)
    soup = BeautifulSoup(resp.text, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(url, href)
        if same_domain_only and urlparse(full).netloc != base_domain:
            continue
        links.add(full)

    results = [check_url(link, timeout=timeout) for link in sorted(links)]
    broken = [r for r in results if not r.get("ok")]

    return {
        "page": url,
        "checked": len(results),
        "broken_count": len(broken),
        "broken": broken,
        "results": results,
    }
