# hacker-tool:generated
import os, sys, unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.proc import monitor

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        self.assertIsNotNone(monitor)

class TestProcPids(unittest.TestCase):
    def test_returns_list(self):
        self.assertIsInstance(monitor._proc_pids(), list)
    def test_returns_integers(self):
        for p in monitor._proc_pids(): self.assertIsInstance(p, int)
    def test_sorted(self):
        r = monitor._proc_pids(); self.assertEqual(r, sorted(r))
    def test_empty_on_oserror(self):
        with patch("os.listdir", side_effect=OSError):
            self.assertEqual(monitor._proc_pids(), [])
    def test_filters_non_numeric(self):
        with patch("os.listdir", return_value=["1","2","net","999"]):
            self.assertEqual(monitor._proc_pids(), [1, 2, 999])

STAT = "1234 (bash) S 1 1234 1234 0 -1 4194304 100 200 10 20 50 30 0 0 20 0 1 0 300 10485760 2048 18446744073709551615"

class TestProcStat(unittest.TestCase):
    def test_returns_dict(self):
        with patch.object(monitor, "_read", return_value=STAT):
            self.assertIsInstance(monitor._proc_stat(1234), dict)
    def test_state_parsed(self):
        with patch.object(monitor, "_read", return_value=STAT):
            self.assertEqual(monitor._proc_stat(1234).get("state"), "S")
    def test_empty_on_missing(self):
        with patch.object(monitor, "_read", return_value=""):
            self.assertEqual(monitor._proc_stat(99999), {})
    def test_rss_is_int(self):
        with patch.object(monitor, "_read", return_value=STAT):
            self.assertIsInstance(monitor._proc_stat(1234).get("rss"), int)

class TestListProcs(unittest.TestCase):
    def test_expected_keys(self):
        for k in ("count","filter","procs"): self.assertIn(k, monitor.list_procs())
    def test_procs_is_list(self):
        self.assertIsInstance(monitor.list_procs()["procs"], list)
    def test_count_matches_len(self):
        r = monitor.list_procs(); self.assertEqual(r["count"], len(r["procs"]))
    def test_filter_wildcard(self):
        self.assertEqual(monitor.list_procs()["filter"], "*")
    def test_filter_stored(self):
        self.assertEqual(monitor.list_procs(filter_name="python")["filter"], "python")
    def test_proc_keys(self):
        for p in monitor.list_procs()["procs"]:
            for k in ("pid","name","state","rss_kb"): self.assertIn(k, p)
    def test_filter_reduces(self):
        self.assertLessEqual(monitor.list_procs(filter_name="ZZZX")["count"],
                             monitor.list_procs()["count"])
    def test_nonexistent_zero(self):
        self.assertEqual(monitor.list_procs(filter_name="ZZZNONEXISTENT_XYZ")["count"], 0)
    def test_pid_is_int(self):
        for p in monitor.list_procs()["procs"]: self.assertIsInstance(p["pid"], int)
    def test_rss_non_negative(self):
        for p in monitor.list_procs()["procs"]: self.assertGreaterEqual(p["rss_kb"], 0)

class TestTopProcs(unittest.TestCase):
    def test_expected_keys(self):
        for k in ("sort_by","showing","procs","mem_total_kb","mem_avail_kb"):
            self.assertIn(k, monitor.top_procs(n=3))
    def test_n_respected(self):
        self.assertLessEqual(len(monitor.top_procs(n=3)["procs"]), 3)
    def test_showing_matches_len(self):
        r = monitor.top_procs(n=5); self.assertEqual(r["showing"], len(r["procs"]))
    def test_default_sort_rss(self):
        self.assertEqual(monitor.top_procs()["sort_by"], "rss_kb")
    def test_sort_cpu(self):
        self.assertEqual(monitor.top_procs(sort_by="cpu_ticks")["sort_by"], "cpu_ticks")
    def test_sort_pid_ascending(self):
        r = monitor.top_procs(sort_by="pid")
        pids = [p["pid"] for p in r["procs"]]
        self.assertEqual(pids, sorted(pids))
    def test_invalid_sort_raises(self):
        with self.assertRaises(ValueError): monitor.top_procs(sort_by="banana")
    def test_rss_descending(self):
        r = monitor.top_procs(n=50, sort_by="rss_kb")
        v = [p["rss_kb"] for p in r["procs"]]
        self.assertEqual(v, sorted(v, reverse=True))
    def test_n_zero_empty(self):
        self.assertEqual(len(monitor.top_procs(n=0)["procs"]), 0)

class TestFindProc(unittest.TestCase):
    def test_expected_keys(self):
        for k in ("count","filter","procs","query"): self.assertIn(k, monitor.find_proc("x"))
    def test_query_stored(self):
        self.assertEqual(monitor.find_proc("python")["query"], "python")
    def test_nonexistent_empty(self):
        r = monitor.find_proc("ZZZNONEXISTENT_XYZ_999")
        self.assertEqual(r["count"], 0); self.assertEqual(r["procs"], [])

class TestKillProc(unittest.TestCase):
    def test_nonexistent_pid_error(self):
        r = monitor.kill_proc(pid=9999999, sig="TERM")
        self.assertFalse(r["sent"]); self.assertIn("error", r)
    def test_expected_keys(self):
        r = monitor.kill_proc(pid=9999999, sig="TERM")
        for k in ("pid","name","signal","sent"): self.assertIn(k, r)
    def test_invalid_signal_raises(self):
        with self.assertRaises(ValueError): monitor.kill_proc(pid=1, sig="NUKE")
    def test_signal_uppercase(self):
        self.assertEqual(monitor.kill_proc(pid=9999999, sig="term")["signal"], "TERM")
    def test_permission_denied(self):
        with patch("os.kill", side_effect=PermissionError),              patch.object(monitor, "_read", return_value="init"):
            r = monitor.kill_proc(pid=1, sig="KILL")
        self.assertFalse(r["sent"])
        self.assertIn("permission", r["error"].lower())
    def test_success_path(self):
        with patch("os.kill", return_value=None),              patch.object(monitor, "_read", return_value="testproc"):
            r = monitor.kill_proc(pid=12345, sig="TERM")
        self.assertTrue(r["sent"]); self.assertEqual(r["name"], "testproc")

MEMINFO = "MemTotal: 8000000 kB\nMemFree: 1000000 kB\nMemAvailable: 3000000 kB\nCached: 2000000 kB\nSwapTotal: 2000000 kB\nSwapFree: 1500000 kB\n"

class TestMemSummary(unittest.TestCase):
    def test_expected_keys(self):
        with patch.object(monitor, "_read", return_value=MEMINFO):
            r = monitor.mem_summary()
        for k in ("total_mb","used_mb","available_mb","free_mb",
                  "cached_mb","swap_total_mb","swap_used_mb","used_pct"):
            self.assertIn(k, r)
    def test_total_mb(self):
        with patch.object(monitor, "_read", return_value=MEMINFO):
            self.assertAlmostEqual(monitor.mem_summary()["total_mb"],
                                   8000000/1024, places=0)
    def test_used_pct_range(self):
        r = monitor.mem_summary()
        self.assertGreaterEqual(r["used_pct"], 0.0)
        self.assertLessEqual(r["used_pct"], 100.0)
    def test_swap_used(self):
        with patch.object(monitor, "_read", return_value=MEMINFO):
            self.assertAlmostEqual(monitor.mem_summary()["swap_used_mb"],
                                   round(500000/1024,1), places=0)
    def test_live_readable(self):
        r = monitor.mem_summary()
        self.assertIsInstance(r["total_mb"], float)
        self.assertGreater(r["total_mb"], 0)
    def test_all_numeric(self):
        r = monitor.mem_summary()
        for k in ("total_mb","used_mb","available_mb","free_mb","cached_mb","used_pct"):
            self.assertIsInstance(r[k], (int, float))

if __name__ == "__main__":
    unittest.main()
