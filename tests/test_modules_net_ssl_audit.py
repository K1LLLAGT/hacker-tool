# hacker-tool:generated
import os, sys, ssl, socket, datetime, unittest
from unittest.mock import MagicMock, patch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from modules.net import ssl_audit

class TestGenerated(unittest.TestCase):
    def test_importable(self): self.assertIsNotNone(ssl_audit)

def _make_cert(days=90, expired=False):
    from datetime import timezone
    now = datetime.datetime.now(timezone.utc)
    na = (now - datetime.timedelta(days=1)) if expired else (now + datetime.timedelta(days=days))
    fmt = "%b %d %H:%M:%S %Y GMT"
    return {
        "subject": ((("commonName","example.com"),),),
        "issuer":  ((("organizationName","Test CA"),),),
        "notBefore": (now - datetime.timedelta(days=30)).strftime(fmt),
        "notAfter":  na.strftime(fmt),
        "subjectAltName": (("DNS","example.com"),("DNS","www.example.com")),
    }

def _mock_conn(cert, version="TLSv1.3", cipher=("TLS_AES_256_GCM_SHA384","TLSv1.3",256)):
    m = MagicMock()
    m.getpeercert.return_value = cert
    m.version.return_value = version
    m.cipher.return_value = cipher
    m.__enter__ = lambda s: s; m.__exit__ = MagicMock(return_value=False)
    return m

class TestAudit(unittest.TestCase):
    def _run(self, cert, version="TLSv1.3",
             cipher=("TLS_AES_256_GCM_SHA384","TLSv1.3",256),
             hsts=True, host="example.com", port=443, verify=True):
        ctx = MagicMock(spec=ssl.SSLContext)
        ctx.wrap_socket.return_value = _mock_conn(cert, version, cipher)
        raw = MagicMock()
        raw.__enter__ = lambda s: s; raw.__exit__ = MagicMock(return_value=False)
        with patch("ssl.create_default_context", return_value=ctx), \
             patch("socket.create_connection", return_value=raw), \
             patch.object(ssl_audit, "_check_hsts", return_value=hsts):
            return ssl_audit.audit(host, port=port, verify=verify)

    def test_returns_expected_keys(self):
        r = self._run(_make_cert())
        for k in ("subject_cn","issuer_cn","not_after","days_to_expiry",
                  "expired","not_yet_valid","sans","protocol","cipher",
                  "cipher_bits","hsts"):
            self.assertIn(k, r, msg=f"missing key: {k}")
    def test_not_expired_cert(self):
        r = self._run(_make_cert(days=60))
        self.assertFalse(r["expired"]); self.assertGreater(r["days_to_expiry"], 0)
    def test_expired_cert_detected(self):
        self.assertTrue(self._run(_make_cert(expired=True))["expired"])
    def test_sans_parsed(self):
        r = self._run(_make_cert())
        self.assertIsInstance(r["sans"], list)
        self.assertIn("example.com", r["sans"])
        self.assertIn("www.example.com", r["sans"])
    def test_subject_cn_extracted(self):
        self.assertEqual(self._run(_make_cert())["subject_cn"], "example.com")
    def test_protocol_stored(self):
        self.assertEqual(self._run(_make_cert(), version="TLSv1.3")["protocol"], "TLSv1.3")
    def test_cipher_bits_stored(self):
        r = self._run(_make_cert(), cipher=("TLS_AES_256_GCM_SHA384","TLSv1.3",256))
        self.assertEqual(r["cipher_bits"], 256)
    def test_hsts_flag_true(self):  self.assertTrue(self._run(_make_cert(), hsts=True)["hsts"])
    def test_hsts_flag_false(self): self.assertFalse(self._run(_make_cert(), hsts=False)["hsts"])
    def test_connection_error_returns_error_key(self):
        with patch("socket.create_connection", side_effect=OSError("refused")):
            r = ssl_audit.audit("unreachable.invalid", port=443)
        self.assertIn("error", r)
    def test_no_verify_returns_result(self):
        ctx = MagicMock(spec=ssl.SSLContext)
        ctx.wrap_socket.return_value = _mock_conn(_make_cert())
        raw = MagicMock()
        raw.__enter__ = lambda s: s; raw.__exit__ = MagicMock(return_value=False)
        with patch("ssl.create_default_context", return_value=ctx), \
             patch("ssl._create_unverified_context", return_value=ctx, create=True), \
             patch("socket.create_connection", return_value=raw), \
             patch.object(ssl_audit, "_check_hsts", return_value=False):
            r = ssl_audit.audit("example.com", verify=False)
        self.assertIn("subject_cn", r)

class TestCheckHsts(unittest.TestCase):
    def test_header_present(self):
        resp = MagicMock(); resp.getheader.return_value = "max-age=31536000"
        conn = MagicMock()
        conn.__enter__ = lambda s: s; conn.__exit__ = MagicMock(return_value=False)
        conn.getresponse.return_value = resp
        with patch("http.client.HTTPSConnection", return_value=conn):
            self.assertTrue(ssl_audit._check_hsts("example.com", 443, 5))
    def test_header_absent(self):
        resp = MagicMock(); resp.getheader.return_value = None
        conn = MagicMock()
        conn.__enter__ = lambda s: s; conn.__exit__ = MagicMock(return_value=False)
        conn.getresponse.return_value = resp
        with patch("http.client.HTTPSConnection", return_value=conn):
            self.assertFalse(ssl_audit._check_hsts("example.com", 443, 5))
    def test_connection_error_returns_false(self):
        with patch("http.client.HTTPSConnection", side_effect=OSError("timeout")):
            self.assertFalse(ssl_audit._check_hsts("unreachable.invalid", 443, 1))

if __name__ == "__main__": unittest.main()
