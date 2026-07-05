"""
modules/device/info.py — Android / Termux device introspection.

Offline-only. Stdlib only. Reads /proc, /sys, and getprop.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess


def _read(path: str, default: str = "unavailable") -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def _getprop(key: str) -> str:
    if shutil.which("getprop"):
        try:
            return subprocess.check_output(
                ["getprop", key], stderr=subprocess.DEVNULL, text=True
            ).strip() or "unavailable"
        except Exception:
            pass
    return "unavailable"


def _run(*cmd) -> str:
    try:
        return subprocess.check_output(list(cmd), stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unavailable"


def device_info() -> dict:
    return {
        "manufacturer": _getprop("ro.product.manufacturer"),
        "model":        _getprop("ro.product.model"),
        "device":       _getprop("ro.product.device"),
        "android":      _getprop("ro.build.version.release"),
        "sdk":          _getprop("ro.build.version.sdk"),
        "build_id":     _getprop("ro.build.id"),
        "fingerprint":  _getprop("ro.build.fingerprint"),
        "arch":         _getprop("ro.product.cpu.abi"),
        "kernel":       _run("uname", "-r"),
    }


def storage_info() -> dict:
    def _parse_df(path: str) -> dict:
        out = _run("df", "-h", path)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[-1] == path:
                return {"total": parts[1], "used": parts[2],
                        "available": parts[3], "use_pct": parts[4]}
        return {"raw": out}

    return {
        "termux_home":      _parse_df(str(Path.home())),
        "internal_storage": _parse_df("/storage/emulated/0"),
        "sdcard_symlink":   str(Path("/sdcard").resolve())
                            if Path("/sdcard").exists() else "not mounted",
    }


def battery_info() -> dict:
    base = Path("/sys/class/power_supply")
    bat = None
    if base.exists():
        for name in ["battery", "Battery", "BAT0", "BAT1"]:
            if (base / name).is_dir():
                bat = base / name
                break
        if bat is None:
            dirs = [d for d in base.iterdir() if d.is_dir()]
            bat = dirs[0] if dirs else None

    if bat is None:
        return {"status": "unavailable", "note": "/sys/class/power_supply not found"}

    def _r(f): return _read(str(bat / f))

    try:
        temp_c = round(int(_r("temp")) / 10, 1)
    except (ValueError, TypeError):
        temp_c = "unavailable"

    try:
        voltage_v = round(int(_r("voltage_now")) / 1_000_000, 2)
    except (ValueError, TypeError):
        voltage_v = "unavailable"

    return {
        "capacity_pct": _r("capacity"),
        "status":       _r("status"),
        "health":       _r("health"),
        "technology":   _r("technology"),
        "temp_celsius": temp_c,
        "voltage_v":    voltage_v,
    }


def network_interfaces() -> dict:
    interfaces = {}

    for flag, family in [("-4", "ipv4"), ("-6", "ipv6")]:
        out = _run("ip", flag, "addr", "show")
        current = None
        for line in out.splitlines():
            m = re.match(r"^\d+:\s+(\S+):", line)
            if m:
                current = m.group(1).rstrip("@")
                interfaces.setdefault(current, {"ipv4": [], "ipv6": []})
            m = re.match(r"\s+inet6?\s+(\S+)", line)
            if m and current:
                interfaces[current][family].append(m.group(1))

    for iface in interfaces:
        interfaces[iface]["state"] = _read(f"/sys/class/net/{iface}/operstate")

    return {"interfaces": interfaces, "hostname": _run("hostname")}


def cpu_info() -> dict:
    raw = _read("/proc/cpuinfo")
    model = "unavailable"
    for line in raw.splitlines():
        if any(k in line for k in ("Hardware", "model name", "Processor")):
            model = line.split(":", 1)[-1].strip()
            break

    cores = raw.lower().count("processor\t:") or os.cpu_count() or "unavailable"

    try:
        freq_mhz = round(int(_read(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")) / 1000, 1)
    except ValueError:
        freq_mhz = "unavailable"

    try:
        max_mhz = round(int(_read(
            "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")) / 1000, 1)
    except ValueError:
        max_mhz = "unavailable"

    return {"model": model, "cores": cores,
            "cur_freq_mhz": freq_mhz, "max_freq_mhz": max_mhz}
