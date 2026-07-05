# hacker-tool:generated
import os, sys, hashlib, json, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from modules.fs.integrity import (_excluded, _hash_file, build_manifest,
                                   compare, DEFAULT_EXCLUDES)

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        from modules.fs import integrity; self.assertIsNotNone(integrity)

class TestExcluded(unittest.TestCase):
    def test_exact_filename_match(self):
        self.assertTrue(_excluded("foo.pyc", ["*.pyc"]))
    def test_glob_on_path_component(self):
        self.assertTrue(_excluded("subdir/__pycache__", ["__pycache__"]))
    def test_partial_path_ancestor_matches(self):
        self.assertTrue(_excluded("a/__pycache__/b.pyc", ["__pycache__"]))
    def test_non_matching_returns_false(self):
        self.assertFalse(_excluded("src/main.py", ["*.pyc", ".git"]))
    def test_multiple_patterns_first_hit(self):
        self.assertTrue(_excluded(".git", [".git", "*.pyc"]))
    def test_dotgit_in_default_excludes(self):
        self.assertTrue(_excluded(".git", DEFAULT_EXCLUDES))
    def test_log_file_in_default_excludes(self):
        self.assertTrue(_excluded("logs/session.log", DEFAULT_EXCLUDES))
    def test_normal_py_file_not_excluded(self):
        self.assertFalse(_excluded("modules/net/scan.py", DEFAULT_EXCLUDES))

class TestHashFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.write(b"hello world"); self.tmp.close()
    def tearDown(self): os.unlink(self.tmp.name)
    def test_sha256_known_digest(self):
        self.assertEqual(_hash_file(self.tmp.name, "sha256"),
                         hashlib.sha256(b"hello world").hexdigest())
    def test_md5_length(self):
        self.assertEqual(len(_hash_file(self.tmp.name, "md5")), 32)
    def test_sha512_length(self):
        self.assertEqual(len(_hash_file(self.tmp.name, "sha512")), 128)
    def test_empty_file_sha256(self):
        t = tempfile.NamedTemporaryFile(delete=False); t.close()
        try:
            self.assertEqual(_hash_file(t.name, "sha256"),
                             hashlib.sha256(b"").hexdigest())
        finally: os.unlink(t.name)

class TestBuildManifest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, "a.txt"), "w") as f: f.write("alpha")
        sub = os.path.join(self.d, "sub"); os.makedirs(sub)
        with open(os.path.join(sub, "b.py"), "w") as f: f.write("beta")
        with open(os.path.join(self.d, "skip.pyc"), "w") as f: f.write("x")
    def tearDown(self):
        import shutil; shutil.rmtree(self.d)
    def test_returns_expected_top_level_keys(self):
        m = build_manifest(self.d, excludes=[])
        for k in ("root","algo","count","files"): self.assertIn(k, m)
    def test_algo_stored_in_manifest(self):
        self.assertEqual(build_manifest(self.d, algo="sha256", excludes=[])["algo"], "sha256")
    def test_root_is_absolute(self):
        self.assertTrue(os.path.isabs(build_manifest(self.d, excludes=[])["root"]))
    def test_count_matches_files_dict(self):
        m = build_manifest(self.d, excludes=[])
        self.assertEqual(m["count"], len(m["files"]))
    def test_pyc_excluded_by_default(self):
        m = build_manifest(self.d)
        self.assertFalse(any(p.endswith(".pyc") for p in m["files"]))
    def test_file_entry_has_hash_and_size(self):
        m = build_manifest(self.d, excludes=[])
        e = next((v for k,v in m["files"].items() if "a.txt" in k), None)
        self.assertIsNotNone(e); self.assertIn("hash", e); self.assertIn("size", e)
    def test_size_correct(self):
        m = build_manifest(self.d, excludes=[])
        e = next((v for k,v in m["files"].items() if "a.txt" in k), None)
        self.assertEqual(e["size"], 5)
    def test_hash_changes_when_content_changes(self):
        m1 = build_manifest(self.d, excludes=[])
        with open(os.path.join(self.d, "a.txt"), "w") as f: f.write("CHANGED!")
        m2 = build_manifest(self.d, excludes=[])
        k = next(k for k in m1["files"] if "a.txt" in k)
        self.assertNotEqual(m1["files"][k]["hash"], m2["files"][k]["hash"])
    def test_empty_directory(self):
        import shutil; d = tempfile.mkdtemp()
        try:
            m = build_manifest(d, excludes=[])
            self.assertEqual(m["count"], 0); self.assertEqual(m["files"], {})
        finally: shutil.rmtree(d)
    def test_custom_excludes_respected(self):
        m = build_manifest(self.d, excludes=["*.txt"])
        self.assertFalse(any(k.endswith(".txt") for k in m["files"]))

class TestCompare(unittest.TestCase):
    BASE = {"algo":"sha256","files":{"a.txt":{"hash":"aaa","size":3},
                                      "b.txt":{"hash":"bbb","size":3}}}
    def test_no_changes(self):
        d = compare(self.BASE, self.BASE)
        self.assertEqual(d["added"],[]); self.assertEqual(d["removed"],[])
        self.assertEqual(d["modified"],[])
    def test_added_file(self):
        cur = {"files": dict(self.BASE["files"]) | {"c.txt":{"hash":"ccc"}}}
        d = compare(self.BASE, cur)
        self.assertIn("c.txt", d["added"]); self.assertEqual(d["removed"],[])
    def test_removed_file(self):
        cur = {"files":{"a.txt":{"hash":"aaa","size":3}}}
        d = compare(self.BASE, cur); self.assertIn("b.txt", d["removed"])
    def test_modified_file(self):
        cur = {"files":{"a.txt":{"hash":"ZZZ","size":3},"b.txt":{"hash":"bbb","size":3}}}
        d = compare(self.BASE, cur); self.assertIn("a.txt", d["modified"])
    def test_result_has_three_keys(self):
        d = compare(self.BASE, self.BASE)
        for k in ("added","removed","modified"): self.assertIn(k, d)
    def test_added_list_is_sorted(self):
        extra = {"z.txt":{"hash":"z"},"a2.txt":{"hash":"a2"}}
        cur = {"files": dict(self.BASE["files"]) | extra}
        d = compare(self.BASE, cur); self.assertEqual(d["added"], sorted(d["added"]))
    def test_roundtrip_via_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.BASE, f); fname = f.name
        try:
            with open(fname) as f: loaded = json.load(f)
            d = compare(loaded, loaded)
            self.assertEqual(d["added"],[]); self.assertEqual(d["removed"],[])
        finally: os.unlink(fname)
    def test_empty_baseline(self):
        d = compare({"files":{}}, self.BASE)
        self.assertEqual(sorted(d["added"]), sorted(self.BASE["files"].keys()))

if __name__ == "__main__": unittest.main()
