# hacker-tool:generated
import os, sys, unittest
from unittest.mock import MagicMock, patch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from modules.web.crawl import crawl, _LinkExtractor, _normalize, _same_host, _clean

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        from modules.web import crawl as m; self.assertIsNotNone(m)

class TestNormalize(unittest.TestCase):
    def test_relative_resolved_against_base(self):
        r = _normalize("http://example.com/a/b", "/c")
        self.assertEqual(r, "http://example.com/c")
    def test_absolute_url_unchanged(self):
        r = _normalize("http://example.com/a", "http://other.com/z")
        self.assertEqual(r, "http://other.com/z")
    def test_fragment_stripped(self):
        r = _normalize("http://example.com/", "http://example.com/page#section")
        self.assertNotIn("#section", r)
    def test_adds_path_to_bare_host(self):
        r = _normalize("http://example.com", "http://example.com")
        self.assertIn("example.com", r)
    def test_relative_path_resolved(self):
        r = _normalize("http://example.com/a/b", "d")
        self.assertIn("example.com", r)

class TestSameHost(unittest.TestCase):
    def test_same_host_true(self):
        self.assertTrue(_same_host("http://example.com/a", "http://example.com/b"))
    def test_different_host_false(self):
        self.assertFalse(_same_host("http://example.com/a", "http://other.org/b"))
    def test_subdomain_is_different(self):
        self.assertFalse(_same_host("http://example.com/", "http://sub.example.com/"))
    def test_same_host_different_paths(self):
        self.assertTrue(_same_host("http://x.com/foo", "http://x.com/bar"))
    def test_returns_bool(self):
        self.assertIsInstance(_same_host("http://a.com/", "https://a.com/"), bool)

class TestClean(unittest.TestCase):
    def test_strips_fragment(self):
        self.assertNotIn("#frag", _clean("http://example.com/page#frag"))
    def test_returns_string(self):
        self.assertIsInstance(_clean("http://example.com/search?q=hello"), str)
    def test_bare_url_contains_host(self):
        self.assertIn("example.com", _clean("http://example.com/path"))

class TestLinkExtractor(unittest.TestCase):
    def _ex(self, html):
        e = _LinkExtractor(); e.feed(html); return e.links
    def test_single_anchor(self):
        self.assertIn("http://example.com/about",
                      self._ex('<a href="http://example.com/about">A</a>'))
    def test_multiple_anchors(self):
        self.assertEqual(len(self._ex('<a href="/a">A</a><a href="/b">B</a>')), 2)
    def test_empty_html(self):
        self.assertEqual(len(self._ex("")), 0)
    def test_anchor_without_href(self):
        self.assertEqual(len(self._ex('<a name="top">Top</a>')), 0)
    def test_nested_tags(self):
        self.assertIn("http://example.com/",
                      self._ex('<div><p><a href="http://example.com/">x</a></p></div>'))
    def test_javascript_does_not_crash(self):
        r = self._ex('<a href="javascript:void(0)">x</a>')
        self.assertIsInstance(r, (list, set))

class TestCrawl(unittest.TestCase):
    START = "http://example.com/"
    PAGE  = (b"<html><body>"
             b'<a href="/about">About</a>'
             b'<a href="/contact">Contact</a>'
             b'<a href="http://external.org/">Ext</a>'
             b"</body></html>")
    STUB  = b"<html><body><a href='/'>Home</a></body></html>"

    def _urlopen(self, pages):
        def _fn(req, timeout=None):
            url = (req if isinstance(req, str) else req.full_url).split("#")[0]
            body = pages.get(url, b"<html></html>")
            r = MagicMock(); r.read.return_value = body
            r.__enter__ = lambda s: s; r.__exit__ = MagicMock(return_value=False)
            return r
        return _fn

    def test_returns_expected_keys(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=1, max_pages=5, delay=0)
        for k in ("start","pages","count"): self.assertIn(k, r)

    def test_start_url_in_result(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=1, max_pages=5, delay=0)
        self.assertIn(self.START, r["start"])

    def test_external_links_excluded(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=1, max_pages=10, delay=0)
        self.assertFalse(any("external.org" in u for u in r["pages"]))

    def test_count_matches_pages_len(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=1, max_pages=5, delay=0)
        self.assertEqual(r["count"], len(r["pages"]))

    def test_max_pages_respected(self):
        pages = {self.START: self.PAGE,
                 "http://example.com/about": self.STUB,
                 "http://example.com/contact": self.STUB}
        with patch("urllib.request.urlopen", side_effect=self._urlopen(pages)):
            r = crawl(self.START, depth=3, max_pages=2, delay=0)
        self.assertLessEqual(r["count"], 2)

    def test_depth_zero_visits_only_start(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=0, max_pages=50, delay=0)
        self.assertEqual(r["count"], 1)

    def test_network_error_handled_gracefully(self):
        with patch("urllib.request.urlopen", side_effect=OSError("down")):
            r = crawl(self.START, depth=1, max_pages=5, delay=0)
        self.assertIn("pages", r)

    def test_pages_value_is_list(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._urlopen({self.START: self.PAGE})):
            r = crawl(self.START, depth=1, max_pages=5, delay=0)
        # at least one page entry exists
        self.assertGreater(len(r["pages"]), 0)
        first_val = next(iter(r["pages"].values()))
        self.assertIsInstance(first_val, list)

if __name__ == "__main__": unittest.main()
