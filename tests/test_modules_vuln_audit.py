# hacker-tool:generated
import os, sys, tempfile, unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.vuln import audit

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        self.assertIsNotNone(audit)

def _mock_resp(headers, status=200, url="https://example.com"):
    from http.client import HTTPMessage
    msg = HTTPMessage()
    for k, v in headers.items(): msg[k] = v
    r = MagicMock()
    r.headers = msg; r.status = status; r.url = url
    r.__enter__ = lambda s: s
    r.__exit__ = MagicMock(return_value=False)
    return r

ALL_HDRS = {
    "strict-transport-security": "max-age=31536000",
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "geolocation=()",
    "x-xss-protection": "1; mode=block",
}

class TestCheckHeaders(unittest.TestCase):
    def test_expected_keys(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp(ALL_HDRS)):
            r = audit.check_headers("https://example.com")
        for k in ("url","status","checked_at","grade","score","present","missing","leaking_info"):
            self.assertIn(k, r)
    def test_all_headers_grade_a(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp(ALL_HDRS)):
            self.assertEqual(audit.check_headers("https://example.com")["grade"], "A")
    def test_no_headers_grade_f(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp({})):
            self.assertEqual(audit.check_headers("https://example.com")["grade"], "F")
    def test_leaky_server_detected(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp({"server": "Apache/2.4"})):
            r = audit.check_headers("https://example.com")
        self.assertIn("server", [h["header"] for h in r["leaking_info"]])
    def test_https_prefix_added(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp({})) as m:
            audit.check_headers("example.com")
        self.assertTrue(m.call_args[0][0].full_url.startswith("https://"))
    def test_url_error_returns_error_key(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("t")):
            self.assertIn("error", audit.check_headers("https://x.invalid"))
    def test_score_format(self):
        with patch("urllib.request.urlopen", return_value=_mock_resp({})):
            r = audit.check_headers("https://example.com")
        self.assertRegex(r["score"], r"^\d+/\d+$")

class TestScanPorts(unittest.TestCase):
    def test_open_port(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"),              patch("socket.create_connection") as m:
            m.return_value.__enter__ = lambda s: s
            m.return_value.__exit__ = MagicMock(return_value=False)
            r = audit.scan_ports("localhost", ports=[22])
        self.assertEqual(r["open_count"], 1)
        self.assertEqual(r["open"][0]["port"], 22)
    def test_closed_port(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"),              patch("socket.create_connection", side_effect=ConnectionRefusedError):
            r = audit.scan_ports("localhost", ports=[19999])
        self.assertEqual(r["open_count"], 0)
        self.assertIn(19999, r["closed"])
    def test_public_ip_rejected(self):
        with patch("socket.gethostbyname", return_value="8.8.8.8"):
            with self.assertRaises(ValueError):
                audit.scan_ports("8.8.8.8", ports=[80])
    def test_rfc1918_accepted(self):
        with patch("socket.gethostbyname", return_value="192.168.1.1"),              patch("socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertIn("host", audit.scan_ports("192.168.1.1", ports=[9999]))
    def test_expected_keys(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"),              patch("socket.create_connection", side_effect=ConnectionRefusedError):
            r = audit.scan_ports("localhost", ports=[65534])
        for k in ("host","resolved","scanned","open_count","open","closed"):
            self.assertIn(k, r)
    def test_ssh_service_hint(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"),              patch("socket.create_connection") as m:
            m.return_value.__enter__ = lambda s: s
            m.return_value.__exit__ = MagicMock(return_value=False)
            r = audit.scan_ports("localhost", ports=[22])
        self.assertEqual(r["open"][0]["service"], "SSH")
    def test_scanned_count(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"),              patch("socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertEqual(audit.scan_ports("localhost", ports=[80,443,8080])["scanned"], 3)
    def test_gaierror_returns_error(self):
        import socket
        with patch("socket.gethostbyname", side_effect=socket.gaierror("nxd")):
            self.assertIn("error", audit.scan_ports("nxd.invalid", ports=[80]))

class TestCheckPerms(unittest.TestCase):
    def test_clean_dir_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ok.txt")
            open(p, "w").write("x"); os.chmod(p, 0o644)
            self.assertEqual(audit.check_perms(d)["findings_count"], 0)
    def test_world_writable_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bad.txt")
            open(p, "w").write("x"); os.chmod(p, 0o666)
            r = audit.check_perms(d)
        self.assertGreater(r["findings_count"], 0)
        self.assertIn("world-writable",
                      [i for f in r["findings"] for i in f["issues"]])
    def test_expected_keys(self):
        with tempfile.TemporaryDirectory() as d:
            for k in ("root","checked","findings_count","findings","errors"):
                self.assertIn(k, audit.check_perms(d))
    def test_root_is_absolute(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(os.path.isabs(audit.check_perms(d)["root"]))
    def test_max_findings_respected(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(10):
                p = os.path.join(d, f"b{i}.txt")
                open(p,"w").write("x"); os.chmod(p, 0o666)
            self.assertLessEqual(audit.check_perms(d, max_findings=3)["findings_count"], 3)
    def test_checked_count_positive(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3): open(os.path.join(d,f"f{i}.txt"),"w").write("x")
            self.assertGreaterEqual(audit.check_perms(d)["checked"], 3)

if __name__ == "__main__":
    unittest.main()
