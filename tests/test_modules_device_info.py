# hacker-tool:generated
import os, sys, tempfile, unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.device import info

class TestGenerated(unittest.TestCase):
    def test_importable(self):
        self.assertIsNotNone(info)

class TestReadHelper(unittest.TestCase):
    def test_missing_returns_default(self):
        self.assertEqual(info._read("/nonexistent/xyz", default="fb"), "fb")
    def test_reads_content(self):
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("  hello  \n"); p = f.name
        try:
            self.assertEqual(info._read(p), "hello")
        finally:
            os.unlink(p)

class TestDeviceInfo(unittest.TestCase):
    def test_returns_expected_keys(self):
        with patch.object(info, "_getprop", return_value="x"),              patch.object(info, "_run", return_value="5.15"):
            r = info.device_info()
        for k in ("manufacturer","model","device","android","sdk",
                  "build_id","fingerprint","arch","kernel"):
            self.assertIn(k, r)
    def test_unavailable_fallback(self):
        with patch.object(info, "_getprop", return_value="unavailable"),              patch.object(info, "_run", return_value="unavailable"):
            self.assertEqual(info.device_info()["manufacturer"], "unavailable")
    def test_kernel_from_uname(self):
        with patch.object(info, "_getprop", return_value="x"),              patch.object(info, "_run", return_value="5.15.104-android13"):
            self.assertEqual(info.device_info()["kernel"], "5.15.104-android13")

class TestStorageInfo(unittest.TestCase):
    DF = "Filesystem Size Used Avail Use% Mounted on\ntmpfs 64M 12M 52M 19% /\n"
    def test_expected_keys(self):
        with patch.object(info, "_run", return_value=self.DF):
            r = info.storage_info()
        for k in ("termux_home","internal_storage","sdcard_symlink"):
            self.assertIn(k, r)
    def test_is_dict(self):
        with patch.object(info, "_run", return_value=self.DF):
            self.assertIsInstance(info.storage_info(), dict)

class TestBatteryInfo(unittest.TestCase):
    def test_temp_conversion(self):
        self.assertEqual(round(310 / 10, 1), 31.0)
    def test_returns_status_key(self):
        from pathlib import Path
        with patch.object(Path, "exists", return_value=False):
            self.assertIn("status", info.battery_info())

class TestNetworkInterfaces(unittest.TestCase):
    IP4 = "1: lo: <LOOPBACK>\n    inet 127.0.0.1/8 scope host lo\n2: wlan0: <BROADCAST>\n    inet 192.168.1.42/24 scope global wlan0\n"
    IP6 = "1: lo: <LOOPBACK>\n    inet6 ::1/128 scope host\n"
    def _mock(*cmd):
        pass
    def test_expected_keys(self):
        def mk(*cmd):
            if "-4" in cmd: return self.IP4
            if "-6" in cmd: return self.IP6
            return "host"
        with patch.object(info, "_run", side_effect=mk),              patch.object(info, "_read", return_value="up"):
            r = info.network_interfaces()
        self.assertIn("interfaces", r); self.assertIn("hostname", r)
    def test_ipv4_parsed(self):
        def mk(*cmd):
            if "-4" in cmd: return self.IP4
            if "-6" in cmd: return self.IP6
            return "host"
        with patch.object(info, "_run", side_effect=mk),              patch.object(info, "_read", return_value="up"):
            r = info.network_interfaces()
        self.assertIn("192.168.1.42/24", r["interfaces"]["wlan0"]["ipv4"])

class TestCpuInfo(unittest.TestCase):
    CPU = "Hardware\t: AArch64 Processor rev 14\nprocessor\t: 0\nprocessor\t: 1\nprocessor\t: 2\nprocessor\t: 3\n"
    def test_expected_keys(self):
        with patch.object(info, "_read", side_effect=lambda p, **kw:
                          self.CPU if "cpuinfo" in p else "1800000"):
            for k in ("model","cores","cur_freq_mhz","max_freq_mhz"):
                self.assertIn(k, info.cpu_info())
    def test_core_count(self):
        with patch.object(info, "_read", side_effect=lambda p, **kw:
                          self.CPU if "cpuinfo" in p else "1000000"):
            self.assertEqual(info.cpu_info()["cores"], 4)
    def test_freq_mhz_conversion(self):
        with patch.object(info, "_read", side_effect=lambda p, **kw:
                          self.CPU if "cpuinfo" in p else "1800000"):
            self.assertEqual(info.cpu_info()["cur_freq_mhz"], 1800.0)

if __name__ == "__main__":
    unittest.main()
