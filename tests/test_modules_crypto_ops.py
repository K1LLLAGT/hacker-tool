# hacker-tool:generated
import os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.crypto import ops

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        self.assertIsNotNone(ops)

class TestHashData(unittest.TestCase):
    def test_sha256_known_digest(self):
        result = ops.hash_data(text="hello", algo="sha256")
        self.assertEqual(result["digest"],
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    def test_returns_expected_keys(self):
        for k in ("source","algo","digest","bytes"):
            self.assertIn(k, ops.hash_data(text="x"))
    def test_source_sentinel(self):
        self.assertEqual(ops.hash_data(text="x")["source"], "<text>")
    def test_byte_count(self):
        self.assertEqual(ops.hash_data(text="hello")["bytes"], 5)
    def test_algo_md5(self):
        r = ops.hash_data(text="hello", algo="md5")
        self.assertEqual(r["digest"], "5d41402abc4b2a76b9719d911017c592")
    def test_algo_sha512_length(self):
        self.assertEqual(len(ops.hash_data(text="a", algo="sha512")["digest"]), 128)
    def test_invalid_algo_raises(self):
        with self.assertRaises(ValueError):
            ops.hash_data(text="x", algo="rot13")
    def test_no_input_raises(self):
        with self.assertRaises((ValueError, TypeError)):
            ops.hash_data()
    def test_file_input(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hacker-tool"); p = f.name
        try:
            r = ops.hash_data(file=p)
            self.assertEqual(r["source"], p)
            self.assertEqual(r["bytes"], 11)
        finally:
            os.unlink(p)
    def test_empty_text(self):
        self.assertEqual(ops.hash_data(text="")["digest"],
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

class TestBase64(unittest.TestCase):
    def test_roundtrip(self):
        enc = ops.encode_b64(text="hacker-tool")
        self.assertEqual(ops.decode_b64(text=enc["result"])["result"], "hacker-tool")
    def test_encode_keys(self):
        for k in ("source","encoding","result"):
            self.assertIn(k, ops.encode_b64(text="x"))
    def test_encoding_label(self):
        self.assertEqual(ops.encode_b64(text="x")["encoding"], "base64")
    def test_urlsafe_label(self):
        self.assertEqual(ops.encode_b64(text="x", url_safe=True)["encoding"], "base64url")
    def test_decode_known(self):
        self.assertEqual(ops.decode_b64(text="aGVsbG8=")["result"], "hello")
    def test_decode_keys(self):
        for k in ("encoding","bytes","result"):
            self.assertIn(k, ops.decode_b64(text="aGVsbG8="))
    def test_urlsafe_roundtrip(self):
        enc = ops.encode_b64(text="hello world", url_safe=True)
        self.assertEqual(ops.decode_b64(text=enc["result"], url_safe=True)["result"], "hello world")
    def test_encode_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00\x01\x02"); p = f.name
        try:
            self.assertIsInstance(ops.encode_b64(file=p)["result"], str)
        finally:
            os.unlink(p)

class TestShannonEntropy(unittest.TestCase):
    def test_uniform_high_entropy(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(bytes(range(256))*4); p = f.name
        try:
            r = ops.shannon_entropy(file=p)
            self.assertGreater(r["entropy"], 7.9)
            self.assertIn("encrypted", r["verdict"])
        finally:
            os.unlink(p)
    def test_single_byte_zero_entropy(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00"*1024); p = f.name
        try:
            r = ops.shannon_entropy(file=p)
            self.assertAlmostEqual(r["entropy"], 0.0, places=4)
            self.assertEqual(r["verdict"], "normal")
        finally:
            os.unlink(p)
    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = f.name
        try:
            r = ops.shannon_entropy(file=p)
            self.assertEqual(r["verdict"], "empty")
        finally:
            os.unlink(p)
    def test_expected_keys(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data"); p = f.name
        try:
            for k in ("file","entropy","max_entropy","size_bytes","verdict"):
                self.assertIn(k, ops.shannon_entropy(file=p))
        finally:
            os.unlink(p)
    def test_max_entropy_eight(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x"); p = f.name
        try:
            self.assertEqual(ops.shannon_entropy(file=p)["max_entropy"], 8.0)
        finally:
            os.unlink(p)

class TestCompareHashes(unittest.TestCase):
    H = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    def test_identical_match(self):
        self.assertTrue(ops.compare_hashes(self.H, self.H)["match"])
    def test_different_no_match(self):
        self.assertFalse(ops.compare_hashes(self.H, "aabbcc"*10)["match"])
    def test_case_insensitive(self):
        self.assertTrue(ops.compare_hashes("AABBCC", "aabbcc")["match"])
    def test_strips_whitespace(self):
        self.assertTrue(ops.compare_hashes("  aabbcc  ", "aabbcc")["match"])
    def test_returns_both_keys(self):
        r = ops.compare_hashes("aa", "bb")
        self.assertIn("hash_a", r); self.assertIn("hash_b", r)

if __name__ == "__main__":
    unittest.main()
