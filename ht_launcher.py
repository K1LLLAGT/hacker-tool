#!/usr/bin/env python3
"""
hacker-tool launcher - interactive TUI menu for the hacker-tool CLI.

Stdlib-only. Runs in Termux / any POSIX terminal.
Arrow-key navigation (termios) with automatic fallback to numbered input.

Wire the COMMANDS table below to your real subcommand/flag syntax,
then run:  python ht_launcher.py
"""

from __future__ import annotations

import ipaddress
import os
import re
import shlex
import shutil
import subprocess
import sys

# --------------------------------------------------------------------- config

# Dynamically resolve path so the tool works from any clone location
_HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = [sys.executable, os.path.join(_HERE, "hacker-tool.py")]

USE_COLOR = True
DRY_RUN = False
BANNER_STYLE = "shadow"
THEME = "cyber"
TRUECOLOR = True

# ------------------------------------------------------------------ COMMANDS

COMMANDS = {
    # ── existing ──────────────────────────────────────────────────────────
    "fs":           ["fs"],
    "net":          ["net"],
    "web":          ["web"],
    "project":      ["project"],
    "sync":         ["sync"],
    "report":       ["report"],
    "net_ping":     ["net", "scan", "--range", "{cidr}"],
    "net_nmap":     ["net", "scan", "--range", "{cidr}", "--nmap"],
    "project_snap": ["project", "snapshot", "{path}",
                     ("--name", "{name}"), ("--out", "{out}")],
    "report_open":  ["report", "--open"],
    "fs_integrity_check":  ["fs", "integrity", "{root}"],
    "fs_integrity_save":   ["fs", "integrity", "{root}", "--save"],
    "fs_integrity_json":   ["fs", "integrity", "{root}", "--json"],
    "net_ssl_audit":       ["net", "ssl-audit", "{target}"],
    "net_ssl_noverify":    ["net", "ssl-audit", "{target}", "--no-verify"],
    "web_crawl":           ["web", "crawl", "{url}", "--depth", "{depth}",
                            "--max", "{max}"],

    # ── crypto ────────────────────────────────────────────────────────────
    "crypto_hash_text":   ["crypto", "hash", "--text", "{text}",
                           ("--algo", "{algo}")],
    "crypto_hash_file":   ["crypto", "hash", "--file", "{file}",
                           ("--algo", "{algo}")],
    "crypto_encode_text": ["crypto", "encode", "--text", "{text}"],
    "crypto_encode_file": ["crypto", "encode", "--file", "{file}"],
    "crypto_decode":      ["crypto", "decode", "--text", "{b64}"],
    "crypto_entropy":     ["crypto", "entropy", "--file", "{file}"],
    "crypto_compare":     ["crypto", "compare",
                           "--hash-a", "{hash_a}", "--hash-b", "{hash_b}"],

    # ── device ────────────────────────────────────────────────────────────
    "device_info":    ["device", "info"],
    "device_storage": ["device", "storage"],
    "device_battery": ["device", "battery"],
    "device_net":     ["device", "net"],
    "device_cpu":     ["device", "cpu"],

    # ── vuln ──────────────────────────────────────────────────────────────
    "vuln_headers": ["vuln", "headers", "{url}"],
    "vuln_ports":   ["vuln", "ports", "--host", "{host}",
                     ("--ports", "{ports}")],
    "vuln_perms":   ["vuln", "perms", "--root", "{root}"],

    # ── proc ──────────────────────────────────────────────────────────────
    "proc_list":        ["proc", "list"],
    "proc_list_filter": ["proc", "list", "--filter", "{filter}"],
    "proc_top":         ["proc", "top", ("--n", "{n}"), ("--sort", "{sort}")],
    "proc_find":        ["proc", "find", "{name}"],
    "proc_kill":        ["proc", "kill", "{pid}", ("--sig", "{sig}")],
    "proc_mem":         ["proc", "mem"],
}

# -------------------------------------------------------------------- MENU

MENU = [
    ("Filesystem    (fs)", "fs"),
    ("Network       (net)", [
        ("Ping sweep    [RFC1918]",  "net_ping"),
        ("Nmap -sn      [RFC1918]",  "net_nmap"),
        ("ARP neighbors [ip neigh]", "net_neigh"),
        ("net (raw args)",           "net"),
    ]),
    ("Web           (web)", "web"),
    ("Project       (project)", [
        ("Snapshot project",   "project_snap"),
        ("project (raw args)", "project"),
    ]),
    ("Sync / SMB    (sync)", "sync"),
    ("Report        (report)", [
        ("Open latest report", "report_open"),
        ("report (raw args)",  "report"),
    ]),
    ("Crypto        (crypto)", [
        ("Hash text string",          "crypto_hash_text"),
        ("Hash file",                 "crypto_hash_file"),
        ("Encode text → base64",      "crypto_encode_text"),
        ("Encode file → base64",      "crypto_encode_file"),
        ("Decode base64 string",      "crypto_decode"),
        ("Entropy  [detect encrypt]", "crypto_entropy"),
        ("Compare two digests",       "crypto_compare"),
    ]),
    ("Device        (device)", [
        ("Device info  [getprop]",   "device_info"),
        ("Storage usage",            "device_storage"),
        ("Battery status + temp",    "device_battery"),
        ("Network interfaces + IPs", "device_net"),
        ("CPU model + frequency",    "device_cpu"),
    ]),
    ("Vuln          (vuln)", [
        ("Header audit  [online]",         "vuln_headers"),
        ("Port scan     [LAN/localhost]",   "vuln_ports"),
        ("Permission audit  [SUID/world]",  "vuln_perms"),
    ]),
    ("Proc          (proc)", [
        ("List all processes",    "proc_list"),
        ("List — filter by name", "proc_list_filter"),
        ("Top N by memory/CPU",   "proc_top"),
        ("Find process by name",  "proc_find"),
        ("Kill process by PID",   "proc_kill"),
        ("Memory summary",        "proc_mem"),
    ]),
    ("Settings", "SETTINGS"),
]

# ------------------------------------------------------------------- banners

BANNERS = {
    "shadow": """
██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗
██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
███████║███████║██║     █████╔╝ █████╗  ██████╔╝
██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
""",
    "thin": r"""
 _            _               _            _
| |_  __ _ __| |_____ _ _ ___| |_ ___  ___| |
| ' \/ _` / _| / / -_) '_|___|  _/ _ \/ _ \ |
|_||_\__,_\__|_\_\___|_|      \__\___/\___/_|
""",
}
SUBTITLE = "// offline-first audit + automation console"

GRADIENTS = {
    "cyber":   {"stops": [(0, 229, 255), (80, 140, 255), (150, 90, 255),
                          (230, 70, 220)], "accent": (120, 160, 255)},
    "vapor":   {"stops": [(255, 110, 180), (180, 100, 255), (90, 160, 255),
                          (0, 230, 230)], "accent": (200, 120, 255)},
    "matrix":  {"stops": [(180, 255, 120), (0, 255, 140), (0, 200, 160)],
                "accent": (0, 230, 140)},
    "fire":    {"stops": [(255, 230, 80), (255, 140, 0), (255, 50, 60),
                          (220, 40, 120)], "accent": (255, 140, 40)},
    "rainbow": {"stops": [(255, 60, 60), (255, 180, 0), (240, 240, 60),
                          (60, 220, 90), (0, 200, 255), (150, 90, 255)],
                "accent": (0, 200, 255)},
}

# --------------------------------------------------------------------- colors

RESET  = "\x1b[0m"
BOLD   = "\x1b[1m"
DIM    = "\x1b[2m"
REV    = "\x1b[7m"
GREEN  = "\x1b[32m"
CYAN   = "\x1b[36m"
YELLOW = "\x1b[33m"
RED    = "\x1b[31m"


def paint(text, *codes):
    if not USE_COLOR or not codes:
        return text
    return "".join(codes) + text + RESET


def _fg(rgb):
    return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def _grad(stops, t):
    if t <= 0: return stops[0]
    if t >= 1: return stops[-1]
    seg = t * (len(stops) - 1)
    i = int(seg)
    f = seg - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


_BASIC_CYCLE = ["\x1b[96m", "\x1b[94m", "\x1b[95m", "\x1b[92m"]


def accent():
    if not USE_COLOR: return ""
    if TRUECOLOR: return _fg(GRADIENTS[THEME]["accent"])
    return CYAN


def wrap(prefix, text):
    if not USE_COLOR or not prefix: return text
    return prefix + text + RESET


def render_banner():
    art = BANNERS[BANNER_STYLE].strip("\n").split("\n")
    if not USE_COLOR:
        return "\n".join("  " + ln for ln in art)
    width = max((len(ln) for ln in art), default=1)
    stops = GRADIENTS.get(THEME, GRADIENTS["cyber"])["stops"]
    out = []
    for row, ln in enumerate(art):
        if TRUECOLOR:
            buf = ["  "]
            for x, ch in enumerate(ln):
                if ch == " ":
                    buf.append(ch)
                else:
                    buf.append(_fg(_grad(stops, x / max(width - 1, 1))) + ch)
            out.append("".join(buf) + RESET)
        else:
            out.append(wrap(_BASIC_CYCLE[row % len(_BASIC_CYCLE)], "  " + ln))
    return "\n".join(out)


def rule(width=46):
    return wrap(accent(), "  " + "\u2500" * width)


def _dim_tag(label):
    if not USE_COLOR: return label
    m = re.search(r"\s*[(\[].*[)\]]\s*$", label)
    if not m: return label
    return label[:m.start()] + DIM + label[m.start():] + RESET


# --------------------------------------------------------------- terminal i/o

try:
    import select, termios, tty
    _RAW_OK = sys.stdin.isatty() and sys.stdout.isatty()
except Exception:
    _RAW_OK = False


def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def read_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


_KEYMAP = {
    "\x1b[A": "up",    "\x1b[B": "down",
    "\x1b[C": "right", "\x1b[D": "left",
    "k": "up",         "j": "down",
    "\r": "enter",     "\n": "enter",
    "\x1b": "back",
    "q": "quit",       "Q": "quit",
    "\x03": "quit",
}


def get_action():
    return _KEYMAP.get(read_key())


def pause(msg="press any key to continue"):
    print(paint("  " + msg, DIM))
    if _RAW_OK:
        read_key()
    else:
        try: input()
        except EOFError: pass


# ------------------------------------------------------------------- chooser

def _render(breadcrumb, options, selected):
    print(render_banner())
    print(wrap(accent() + DIM, "  " + SUBTITLE))
    print(rule())
    print(wrap(accent(), "  " + " \u203a ".join(breadcrumb)))
    print()
    for i, opt in enumerate(options):
        if i == selected:
            print(wrap(accent() + BOLD, "\u258c \u276f " + opt))
        else:
            print("    " + _dim_tag(opt))
    print()
    print(paint("  \u2191/\u2193 move \u00b7 Enter select \u00b7 Esc back \u00b7 q quit", DIM))
    if DRY_RUN:
        print(paint("  \u25cf dry-run", YELLOW))


def _choose_arrows(breadcrumb, options):
    idx = 0
    while True:
        clear()
        _render(breadcrumb, options, idx)
        act = get_action()
        if act == "up":          idx = (idx - 1) % len(options)
        elif act == "down":      idx = (idx + 1) % len(options)
        elif act in ("enter", "right"): return idx
        elif act in ("back", "left"):   return None
        elif act == "quit":      raise SystemExit


def _choose_numbered(breadcrumb, options):
    while True:
        clear()
        print(render_banner())
        print(wrap(accent() + DIM, "  " + SUBTITLE))
        print(rule())
        print(wrap(accent(), "  " + " \u203a ".join(breadcrumb)))
        print()
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {_dim_tag(opt)}")
        print()
        if DRY_RUN:
            print("  [dry-run]")
        raw = input("  select # (b=back, q=quit): ").strip().lower()
        if raw in ("q", "quit"):  raise SystemExit
        if raw in ("b", "back", ""): return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1


def choose(breadcrumb, options):
    if _RAW_OK: return _choose_arrows(breadcrumb, options)
    return _choose_numbered(breadcrumb, options)


# --------------------------------------------------------------------- guards

_RFC1918 = [ipaddress.ip_network(b) for b in
            ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def is_rfc1918(cidr):
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False
    return net.version == 4 and any(net.subnet_of(b) for b in _RFC1918)


# ------------------------------------------------------------------- prompts

def prompt_cidr():
    while True:
        val = input(paint("  target CIDR (RFC1918 only, blank=cancel): ", CYAN)).strip()
        if not val: return None
        if is_rfc1918(val): return val
        print(paint("  refused: private ranges only (10/8, 172.16/12, 192.168/16).", RED))


def prompt_choice(label, choices, default=None):
    """Prompt constrained to a fixed set of choices."""
    opts = "/".join(choices)
    hint = f"  {label} [{opts}]"
    if default: hint += f" (blank={default})"
    hint += ": "
    while True:
        val = input(paint(hint, CYAN)).strip()
        if not val and default: return default
        if val in choices: return val
        print(paint(f"  choose one of: {opts}", RED))


def prompt_token(token):
    """Resolve a {{token}} placeholder to a concrete argv value."""
    # ── routing ──────────────────────────────────────────────────────────
    if token == "cidr":
        return prompt_cidr()

    if token == "algo":
        return prompt_choice("algo",
                             ["sha256", "sha1", "md5", "sha512", "sha224", "sha384"],
                             default="sha256")

    if token == "b64":
        val = input(paint("  base64 string to decode: ", CYAN)).strip()
        return val or None

    if token == "hash_a":
        val = input(paint("  first digest  (hex): ", CYAN)).strip()
        return val or None

    if token == "hash_b":
        val = input(paint("  second digest (hex): ", CYAN)).strip()
        return val or None

    if token == "text":
        val = input(paint("  text input: ", CYAN)).strip()
        return val or None

    if token in ("file", "path", "root"):
        label = {"file": "file path", "path": "project path",
                 "root": "directory path"}.get(token, token)
        val = input(paint(f"  {label}: ", CYAN)).strip()
        return val or None

        if token == "target":
        return input("  Target host[:port] (e.g. example.com:443): ").strip()
    if token == "depth":
        return input("  Crawl depth [2]: ").strip() or "2"
    if token == "max":
        return input("  Max pages [50]: ").strip() or "50"
    if token == "delay":
        return input("  Delay between requests (sec) [0.5]: ").strip() or "0.5"
    if token == "url":
        val = input(paint("  URL (https:// added if missing): ", CYAN)).strip()
        return val or None

    if token == "host":
        val = input(paint("  host / IP (RFC1918 or localhost only): ", CYAN)).strip()
        return val or None

    if token == "ports":
        val = input(paint("  ports (comma-separated, blank=well-known set): ", CYAN)).strip()
        return val or None

    if token == "pid":
        while True:
            val = input(paint("  PID: ", CYAN)).strip()
            if not val: return None
            if val.isdigit(): return val
            print(paint("  PID must be a whole number.", RED))

    if token == "sig":
        return prompt_choice("signal", ["TERM", "KILL", "HUP", "INT"], default="TERM")

    if token == "n":
        val = input(paint("  number of results (blank=10): ", CYAN)).strip()
        return val if (val and val.isdigit()) else "10"

    if token == "sort":
        return prompt_choice("sort by", ["rss_kb", "cpu_ticks", "pid"],
                             default="rss_kb")

    if token in ("filter", "name"):
        label = "filter name (substring match)" if token == "filter" \
                else "process name (substring)"
        val = input(paint(f"  {label}: ", CYAN)).strip()
        return val or None

    # ── generic fallback ─────────────────────────────────────────────────
    val = input(paint(f"  {token}: ", CYAN)).strip()
    return val or None


def prompt_optional(flag, name):
    """Prompt for an optional flag value. Blank → skip the flag entirely."""
    val = input(paint(f"  {flag} {name} (blank = skip): ", CYAN)).strip()
    return val or None


# ------------------------------------------------------------------- execute

def tool_available():
    exe = TOOL[0]
    return shutil.which(exe) is not None or os.path.exists(exe)


def build_argv(action_id):
    template = COMMANDS.get(action_id)
    if template is None:
        return None
    argv = []
    for part in template:
        if isinstance(part, tuple):
            flag, token = part
            val = prompt_optional(flag, token.strip("{}"))
            if val:
                argv.extend([flag, val])
        elif part.startswith("{") and part.endswith("}"):
            val = prompt_token(part[1:-1])
            if val is None:
                return "CANCELLED"
            argv.append(val)
        else:
            argv.append(part)
    return TOOL + argv


# -------------------------------------------------------------- local helpers

_NEIGH_STATES = {"REACHABLE", "STALE", "DELAY", "PROBE", "FAILED",
                 "INCOMPLETE", "NOARP", "PERMANENT", "NONE"}


def parse_neigh(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if not parts: continue
        ip = parts[0]; mac = iface = ""
        state = parts[-1] if parts[-1] in _NEIGH_STATES else ""
        if "dev" in parts:
            i = parts.index("dev")
            if i + 1 < len(parts): iface = parts[i + 1]
        if "lladdr" in parts:
            i = parts.index("lladdr")
            if i + 1 < len(parts): mac = parts[i + 1]
        rows.append((ip, mac, state, iface))
    return rows


def _ip_key(row):
    try: return (0, int(ipaddress.ip_address(row[0])))
    except ValueError: return (1, 0)


def _state_color(state):
    if state == "REACHABLE": return GREEN
    if state in ("FAILED", "INCOMPLETE"): return RED
    return YELLOW


def show_neighbors():
    print(paint("  ARP / neighbor table  (ip neigh show)", CYAN, BOLD))
    print()
    try:
        res = subprocess.run(["ip", "neigh", "show"],
                             capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        print(paint("  'ip' not found — pkg install iproute2", RED)); return
    except subprocess.TimeoutExpired:
        print(paint("  'ip neigh' timed out.", RED)); return
    rows = parse_neigh(res.stdout)
    if not rows:
        print(paint("  neighbor table empty — run a ping sweep first.", DIM)); return
    rows.sort(key=_ip_key)
    print(f"  {'IP':<16}{'MAC':<20}{'STATE':<12}IFACE")
    print(paint("  " + "-" * 54, DIM))
    for ip, mac, state, iface in rows:
        st = paint(f"{state or '-':<12}", _state_color(state))
        print(f"  {ip:<16}{mac or '-':<20}" + st + iface)
    print()
    print(paint(f"  {len(rows)} neighbor(s)", DIM))


LOCAL_ACTIONS = {
    "net_neigh": show_neighbors,
}


def run(action_id):
    if action_id in LOCAL_ACTIONS:
        clear()
        LOCAL_ACTIONS[action_id]()
        print()
        pause("done")
        return
    clear()
    argv = build_argv(action_id)
    if argv is None:
        pause(paint(f"no command mapped for {action_id!r}", RED)); return
    if argv == "CANCELLED":
        return
    print(paint("  $ " + " ".join(shlex.quote(a) for a in argv), GREEN, BOLD))
    print()
    if DRY_RUN:
        pause(paint("(dry-run) not executed", YELLOW)); return
    try:
        subprocess.run(argv)
    except FileNotFoundError:
        print(paint(f"  could not execute {TOOL[0]!r}.", RED))
        print("  Fix TOOL at the top of the script, or enable Dry-run in Settings.")
    except KeyboardInterrupt:
        print(paint("\n  ^C interrupted", YELLOW))
    print()
    pause("done")


# ------------------------------------------------------------------ settings

def settings_menu(breadcrumb):
    global DRY_RUN, USE_COLOR, TRUECOLOR, THEME
    while True:
        found = "found" if tool_available() else "NOT FOUND"
        opts = [
            f"Dry-run  : {'ON' if DRY_RUN else 'off'}",
            f"Color    : {'ON' if USE_COLOR else 'off'}",
            f"Truecolor: {'ON' if TRUECOLOR else 'off'}",
            f"Theme    : {THEME}",
            f"Banner   : {BANNER_STYLE}",
            f"Tool     : {' '.join(TOOL)}  [{found}]",
            "Back",
        ]
        c = choose(breadcrumb, opts)
        if c is None or c == 6: return
        if   c == 0: DRY_RUN   = not DRY_RUN
        elif c == 1: USE_COLOR  = not USE_COLOR
        elif c == 2: TRUECOLOR  = not TRUECOLOR
        elif c == 3:
            keys = list(GRADIENTS)
            THEME = keys[(keys.index(THEME) + 1) % len(keys)]
        elif c == 4: _cycle_banner()
        elif c == 5:
            clear()
            pause("Edit TOOL at the top of the script to change this.")


def _cycle_banner():
    global BANNER_STYLE
    keys = list(BANNERS)
    BANNER_STYLE = keys[(keys.index(BANNER_STYLE) + 1) % len(keys)]


# ---------------------------------------------------------------- navigation

def run_menu(node, breadcrumb):
    while True:
        top = len(breadcrumb) == 1
        labels = [lbl for lbl, _ in node] + ["Quit" if top else "Back"]
        choice = choose(breadcrumb, labels)
        if choice is None or choice == len(node): return
        label, child = node[choice]
        crumb = label.split()[0].strip("()")
        if child == "SETTINGS":
            settings_menu(breadcrumb + ["Settings"])
        elif isinstance(child, list):
            run_menu(child, breadcrumb + [crumb])
        else:
            run(child)


def main():
    global DRY_RUN
    if not tool_available():
        clear()
        print(paint(f"  warning: {TOOL[0]!r} not found on PATH.", YELLOW))
        print("  Running in dry-run until TOOL is fixed or the tool is installed.")
        print()
        DRY_RUN = True
        pause()
    try:
        run_menu(MENU, ["hacker-tool"])
    except (KeyboardInterrupt, SystemExit):
        pass
    clear()
    print("bye.")


if __name__ == "__main__":
    main()
