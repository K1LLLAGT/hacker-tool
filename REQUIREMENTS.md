# hacker-tool — Installation Requirements

A complete listing of everything hacker-tool and its launcher need. The core
runtime is **stdlib-only Python** — most entries below are only needed for
specific features (network scanning, SMB sync, self-update, etc.).

---

## 1. Platform

| Requirement | Notes |
|---|---|
| **Android + Termux** | Install Termux from **F-Droid** or GitHub, **not** the Play Store build (deprecated and outdated). |
| **Python 3.11+** | Developed/tested on **3.13**. `pkg install python`. |
| Home path | `$HOME` = `/data/data/com.termux/files/home`; project lives at `$HOME/hacker-tool`. |

Also runs on any POSIX shell (Kali on the ROG Strix, the rooted Tab S7, a Pi, etc.) — the requirements below map to `apt`/`pkg` equivalently.

---

## 2. Core runtime (required)

| Package | Provides | Install (Termux) |
|---|---|---|
| `python` | Python 3.11+ interpreter | `pkg install python` |

**No pip runtime dependencies.** hacker-tool and `ht_launcher.py` are both
stdlib-only. `requirements.txt` in the repo is for dev extras only (see §5).

---

## 3. Per-feature dependencies (install only what you use)

| Feature | Needs | Install | Notes |
|---|---|---|---|
| `net scan` (ping sweep) | `ping` | usually preinstalled | RFC1918 ranges only. |
| `net scan --nmap` | `nmap` | `pkg install nmap` | Uses `nmap -sn` for host discovery. |
| Launcher → **ARP neighbors** | `ip` (iproute2) | `pkg install iproute2` | proot-safe ARP view; Android's `/system/bin/ip` may also work, iproute2 is more reliable. |
| `sync` (SMB target) | `smbclient` | `pkg install samba` | Only for SMB destinations. Plain path-to-path sync needs nothing extra. |
| `report` (open HTML) | a browser / `termux-open` | `pkg install termux-api` + Termux:API app | Optional; needed only to auto-open rendered reports. |
| Reports on shared storage | storage permission | run `termux-setup-storage` | Grants `~/storage` and `/sdcard` access. |
| Launcher gradient banner | truecolor terminal | Termux default (24-bit) | If colors garble, toggle **Truecolor OFF** in the launcher's Settings. |
| Banner block glyphs | monospace font w/ box-drawing | Termux default is fine | Optional: a Nerd Font via `~/.termux/font.ttf` for crisper glyphs. |
| **Self-update** (`htctl update`) | `git` | `pkg install git` | Enables pull-based upgrades and version tracking. |

---

## 4. One-liner bootstrap (everything)

Installs the full set at once (skip lines you don't need):

```bash
pkg update && pkg upgrade -y
pkg install -y python git nmap iproute2 samba
termux-setup-storage        # grant storage access when prompted
```

`htctl deps` (see the docs) does this interactively and reports what's missing.

---

## 5. Developer / optional extras

Only needed if you run the test suite or type-check the code.

| Tool | Purpose | Install |
|---|---|---|
| `pytest` | run `tests/` (the 9/9 suite) | `pip install pytest` |
| `mypy` | type-check via `mypy.ini` | `pip install mypy` |

```bash
pip install pytest mypy
```

The bundled `hacker_tool_audit.py` runs structural checks **without** pytest, so
you can validate the tree even on a minimal install.

---

## 6. Quick verification

After installing, confirm the environment:

```bash
python --version                       # 3.11+
python hacker-tool.py --help           # lists fs/net/web/project/sync/report
command -v nmap ip smbclient git       # optional-feature tools present?
```

Or let the manager do it in one shot: `htctl doctor`.
