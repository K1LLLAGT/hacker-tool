# hacker-tool

A single-entrypoint, **offline-first** audit & automation CLI for Termux/Android,
with an interactive TUI launcher. Stdlib-only Python, RFC1918-guarded networking,
opt-in web checks.

- **CLI** — `hacker-tool.py`, six verbs: `fs`, `net`, `web`, `project`, `sync`, `report`.
- **Launcher** — `ht_launcher.py`, an arrow-key menu that wraps the CLI so you don't memorize flags.
- **Manager** — `htctl`, installs deps and updates/backs up the tool from inside Termux.

---

## Contents

1. [Quick start](#quick-start)
2. [Requirements](#requirements)
3. [Install](#install)
4. [Running it](#running-it)
5. [Command reference](#command-reference)
6. [The launcher](#the-launcher)
7. [Configuration](#configuration)
8. [Managing & upgrading (htctl)](#managing--upgrading-htctl)
9. [Making changes](#making-changes)
10. [Troubleshooting](#troubleshooting)
11. [Project layout](#project-layout)
12. [Safety notes](#safety-notes)

---

## Quick start

```bash
pkg install -y python git nmap iproute2      # core + common features
cd ~/hacker-tool
python hacker-tool.py --help                 # CLI
python ht_launcher.py                         # interactive menu
```

---

## Requirements

Core is just **Python 3.11+** (tested on 3.13), stdlib-only — no pip runtime
deps. Individual features add small system packages (nmap, iproute2, samba, git).
See **[REQUIREMENTS.md](REQUIREMENTS.md)** for the full per-feature matrix and a
one-liner bootstrap.

---

## Install

1. **Install Termux** from F-Droid (not the Play Store build).
2. **Install packages:**
   ```bash
   pkg update && pkg upgrade -y
   pkg install -y python git nmap iproute2
   termux-setup-storage        # for reports on /sdcard
   ```
3. **Place the project** at `~/hacker-tool` (clone your repo, or copy the files).
4. **Verify:**
   ```bash
   cd ~/hacker-tool
   python hacker-tool.py --help
   ```
5. *(Optional but recommended)* install global commands with the manager:
   ```bash
   chmod +x htctl
   ./htctl link          # adds: htctl, ht (launcher), hackertool (cli) to PATH
   ```

---

## Running it

Two front-ends over the same code:

| | Command | Best for |
|---|---|---|
| **Launcher (TUI)** | `python ht_launcher.py` or `ht` | Day-to-day; no flags to remember. |
| **CLI (direct)** | `python hacker-tool.py <verb> …` or `hackertool <verb> …` | Scripting, exact flags, automation. |

Discover any command's flags with `--help` at any level:

```bash
python hacker-tool.py --help
python hacker-tool.py net --help
python hacker-tool.py net scan --help
```

---

## Command reference

The **authoritative** flags for each verb are always `--help`. Confirmed usage:

### `fs` — filesystem manifest / integrity / diff
Builds/compares manifests of a directory tree. Run `fs --help` for subcommands
and options.

### `net` — local LAN inventory (RFC1918 only)
Host discovery on networks **you** own. The range **must** be private
(10/8, 172.16/12, 192.168/16) — public ranges are refused.

```bash
python hacker-tool.py net scan --range 10.0.0.0/24            # ping sweep
python hacker-tool.py net scan --range 10.0.0.0/24 --nmap     # nmap -sn
```

### `web` — HTTP checks (online, opt-in)
Checks for sites you operate. Online and explicitly opt-in. See `web --help`.

### `project` — project snapshot / packaging
```bash
python hacker-tool.py project snapshot <project_dir>
python hacker-tool.py project snapshot . --name pre-refactor --out reports/
```
`--name` and `--out` are optional. `<project_dir>` is positional (`.` = current dir).

### `sync` — workspace sync (SMB or path)
Syncs a local workspace to/from a remote SMB share or another path. SMB targets
need `smbclient` (`pkg install samba`). See `sync --help`.

### `report` — render a result as Markdown/HTML
Turns a JSON result into a Markdown/HTML report. See `report --help` for input
and open/format flags.

---

## The launcher

`ht_launcher.py` is a stdlib-only TUI that shells out to `hacker-tool.py`.

**Navigation**
- `↑/↓` (or `j/k`) move · `Enter` select · `Esc`/`←` back · `q` quit
- Falls back to a numbered menu automatically when there's no TTY.

**Menu map**
- Filesystem, Network, Web, Project, Sync, Report — mirror the CLI verbs.
- **Network** adds quick actions: *Ping sweep* / *Nmap -sn* (both prompt for an
  RFC1918 range and refuse public ones), plus **ARP neighbors** — a proot-safe
  `ip neigh` table (IP / MAC / state / iface, sorted, color-coded).
- **Project → Snapshot** prompts for the dir, then optional `--name`/`--out`
  (blank = skip the flag entirely).
- Any verb also has a **(raw args)** entry for free-form flags.

**Settings (live, no file edits)**
- **Dry-run** — print the composed command instead of executing.
- **Color / Truecolor** — full mono mode, or 8-color fallback if 24-bit garbles.
- **Theme** — cycle gradients: `cyber`, `vapor`, `matrix`, `fire`, `rainbow`.
- **Banner** — `shadow` (block art) or `thin` (compact full-name).

**Wiring** — the top of the launcher has two blocks tied to your CLI:
`TOOL` (how it's invoked) and `COMMANDS` (argv templates, with `{tokens}`
prompted at runtime and `(flag, "{token}")` tuples for skippable options).

---

## Configuration

- **`config.yml`** — hacker-tool's own settings. Edit with `htctl edit` (opens
  `config.yml` by default) or `htctl edit config.yml`.
- **Launcher** — `TOOL` and `COMMANDS` at the top of `ht_launcher.py`; look/feel
  defaults `THEME`, `BANNER_STYLE`, `TRUECOLOR` (all also live-toggleable in Settings).

---

## Managing & upgrading (htctl)

`htctl` is a Termux-native manager. Run `./htctl help` for the full list.

| Command | What it does |
|---|---|
| `htctl deps` | Install/verify Termux packages (python, git, nmap, iproute2, optional samba) + storage. |
| `htctl doctor` | Environment health check: versions, tools, files, `--help` sanity, git status. |
| `htctl update` | Back up, then `git pull --ff-only` (auto-stashes local changes), then run tests. |
| `htctl backup` | Timestamped `.tar.gz` of the project into `~/hacker-tool-backups/`. |
| `htctl test` | Run `pytest` (or fall back to `hacker_tool_audit.py`). |
| `htctl edit [file]` | Open a file (default `config.yml`) in `$EDITOR`. |
| `htctl version` | Show `VERSION`/commit. |
| `htctl run` | Launch the TUI. |
| `htctl cli …` | Pass args straight to `hacker-tool.py`. |
| `htctl link` / `unlink` | Add/remove global `htctl`, `ht`, `hackertool` commands. |
| `htctl uninstall` | Back up, then remove the project and linked commands (confirmed). |

**Typical upgrade:**
```bash
htctl update        # backup → fetch → ff-pull (autostash) → tests
```
Set your remote once for pull-based updates: `export HT_REMOTE=git@github.com:K1LLLAGT/hacker-tool.git`
(or edit `HT_REMOTE` at the top of `htctl`).

---

## Making changes

hacker-tool is modular — verbs live under `modules/`, shared code under `core/`.

1. Edit a module: `htctl edit modules/net/scan.py` (or any path).
2. Validate structure without pytest: `python hacker_tool_audit.py`.
3. Run the suite: `htctl test`.
4. Type-check (optional): `mypy .`.
5. Snapshot before big changes: `htctl backup`.

**Paste-safe edits in Termux.** When copy-paste risks corrupting a file
(long content, special chars), write it via a base64 heredoc instead of pasting
source directly:
```bash
base64 -d > path/to/file.py <<'EOF'
<base64 blob>
EOF
```
This decodes byte-for-byte with no paste mangling — the same method used to ship
`ht_launcher.py` updates.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `command not found: hacker-tool` | It's a script, not an alias-visible binary. Use `python hacker-tool.py …`, or `htctl link` for a global `hackertool`. |
| Launcher: *"'hacker-tool' not found on PATH"* | `TOOL` at the top of `ht_launcher.py` must point at the real entry, e.g. `["python", "/data/data/com.termux/files/home/hacker-tool/hacker-tool.py"]`. |
| `net scan` refused a range | By design — only RFC1918 (10/8, 172.16/12, 192.168/16) is allowed. |
| ARP view: *"'ip' not found"* | `pkg install iproute2`. |
| `--nmap` fails | `pkg install nmap`. |
| SMB `sync` fails | `pkg install samba` (provides `smbclient`); check the target in `config.yml`. |
| Banner colors look like garbage | Settings → **Truecolor OFF** (8-color fallback), or **Color OFF** for mono. |
| Scanning fails inside proot | Raw sockets are restricted in proot — run network scans from Termux proper; use **ARP neighbors** (`ip neigh`) inside proot. |
| Reports can't reach `/sdcard` | Run `termux-setup-storage` and re-open Termux. |
| Tests won't run | `pip install pytest`, or run `python hacker_tool_audit.py`. |

---

## Project layout

```
hacker-tool/
├── hacker-tool.py        # entry point (wraps cli.py)
├── cli.py                # argparse dispatcher (fs/net/web/project/sync/report)
├── ht_launcher.py        # interactive TUI launcher
├── htctl                 # Termux manager / updater  (this doc's §8)
├── config.yml            # tool configuration
├── requirements.txt      # dev extras only (runtime is stdlib-only)
├── mypy.ini              # type-check config
├── core/                 # shared code
├── modules/              # per-verb implementations (net/scan.py, …)
├── data/                 # bundled data
├── docs/                 # documentation (this file, REQUIREMENTS.md)
├── reports/              # generated reports
├── workspaces/           # sync workspaces
├── tests/                # pytest suite
├── hacker_tool_audit.py  # structural self-check (no pytest needed)
├── clean.py / fix_main.py# maintenance helpers
└── ...
```

---

## Safety notes

- **Network scanning is RFC1918-only**, enforced both in the CLI (`--range`) and
  in the launcher before a command is ever built. It's for inventorying networks
  you own.
- **Web checks are opt-in and for sites you operate.**
- `htctl update`/`uninstall` **back up first** and ask before anything destructive.
