"""
modules/proc/monitor.py — process inspection for Termux / Android.

Offline-only. Stdlib only. Reads /proc directly.
"""
import os
from pathlib import Path
import signal


def _read(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def _proc_pids() -> list:
    try:
        return sorted(int(e) for e in os.listdir("/proc") if e.isdigit())
    except OSError:
        return []


def _proc_stat(pid: int) -> dict:
    raw = _read(f"/proc/{pid}/stat")
    if not raw:
        return {}
    start = raw.rfind(")")
    if start == -1:
        return {}
    fields = raw[start + 2:].split()
    try:
        return {"state": fields[0], "utime": int(fields[11]),
                "stime": int(fields[12]), "rss": int(fields[21])}
    except (IndexError, ValueError):
        return {}


def _page_size() -> int:
    try:
        return os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, ValueError):
        return 4096


def list_procs(filter_name: str = None) -> dict:
    """List all running processes visible under /proc."""
    page = _page_size()
    procs = []
    for pid in _proc_pids():
        cmdline = _read(f"/proc/{pid}/cmdline").replace("\x00", " ").strip()
        name    = _read(f"/proc/{pid}/comm")
        st      = _proc_stat(pid)
        if not name and not cmdline:
            continue
        if filter_name and filter_name.lower() not in (name + cmdline).lower():
            continue
        procs.append({"pid": pid, "name": name or cmdline[:32],
                      "cmdline": cmdline[:120], "state": st.get("state", "?"),
                      "rss_kb": (st.get("rss", 0) * page) // 1024})
    return {"count": len(procs), "filter": filter_name or "*", "procs": procs}


def top_procs(n: int = 10, sort_by: str = "rss_kb") -> dict:
    """Top N processes sorted by rss_kb, cpu_ticks, or pid."""
    if sort_by not in ("rss_kb", "cpu_ticks", "pid"):
        raise ValueError("sort_by must be: rss_kb, cpu_ticks, or pid")
    page = _page_size()
    procs = []
    for pid in _proc_pids():
        cmdline = _read(f"/proc/{pid}/cmdline").replace("\x00", " ").strip()
        name    = _read(f"/proc/{pid}/comm")
        st      = _proc_stat(pid)
        if not name and not cmdline:
            continue
        procs.append({"pid": pid, "name": name or cmdline[:32],
                      "state": st.get("state", "?"),
                      "rss_kb": (st.get("rss", 0) * page) // 1024,
                      "cpu_ticks": st.get("utime", 0) + st.get("stime", 0)})

    procs.sort(key=lambda p: p.get(sort_by, 0), reverse=(sort_by != "pid"))

    raw = _read("/proc/meminfo")
    mem = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            mem[parts[0].rstrip(":")] = parts[1]

    return {"sort_by": sort_by, "showing": min(n, len(procs)),
            "mem_total_kb": mem.get("MemTotal"), "mem_avail_kb": mem.get("MemAvailable"),
            "procs": procs[:n]}


def find_proc(name: str) -> dict:
    result = list_procs(filter_name=name)
    result["query"] = name
    return result


def kill_proc(pid: int, sig: str = "TERM") -> dict:
    """Send TERM/KILL/HUP/INT to a process by PID."""
    sig_map = {"TERM": signal.SIGTERM, "KILL": signal.SIGKILL,
               "HUP": signal.SIGHUP,  "INT":  signal.SIGINT}
    if sig.upper() not in sig_map:
        raise ValueError(f"Unknown signal '{sig}'. Use: {', '.join(sig_map)}")
    name = _read(f"/proc/{pid}/comm") or "unknown"
    try:
        os.kill(pid, sig_map[sig.upper()])
        return {"pid": pid, "name": name, "signal": sig.upper(), "sent": True}
    except ProcessLookupError:
        return {"pid": pid, "name": name, "signal": sig.upper(),
                "sent": False, "error": "process not found"}
    except PermissionError:
        return {"pid": pid, "name": name, "signal": sig.upper(),
                "sent": False, "error": "permission denied"}


def mem_summary() -> dict:
    """Parse /proc/meminfo into a human-readable summary."""
    raw = {}
    for line in _read("/proc/meminfo").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            raw[parts[0].rstrip(":")] = int(parts[1]) if parts[1].isdigit() else parts[1]

    def kb(k): return raw.get(k, 0)
    def mb(k): return round(kb(k) / 1024, 1)
    total = kb("MemTotal")
    avail = kb("MemAvailable")
    used  = total - avail

    return {"total_mb": mb("MemTotal"), "used_mb": round(used / 1024, 1),
            "available_mb": mb("MemAvailable"), "free_mb": mb("MemFree"),
            "cached_mb": mb("Cached"),
            "swap_total_mb": mb("SwapTotal"),
            "swap_used_mb": round((kb("SwapTotal") - kb("SwapFree")) / 1024, 1),
            "used_pct": round(used / total * 100, 1) if total else 0}
