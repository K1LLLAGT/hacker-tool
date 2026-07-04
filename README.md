<div align="center">

```
  /\_____/\
 /  o   o  \     H A C K E R - T O O L
( ==  ^  == )    ─────────────────────
 )         (     by K1LLLAGT
(           )
 \  |   |  /
_.|___|___| _
```

[![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square)](https://github.com/K1LLLAGT/hacker-tool)
[![Bootstrap](https://img.shields.io/badge/bootstrap-CAT--style%20v2.0.0-cyan?style=flat-square)](./bootstrap.sh)
[![Python](https://img.shields.io/badge/python-3.9%2B-yellow?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](./LICENSE)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Full Requirements Reference](./REQUIREMENTS.md)
- [Quick Start — One-Command Bootstrap](#quick-start--one-command-bootstrap)
- [Termux / Android Setup](#termux--android-setup)
- [What the Bootstrap Does](#what-the-bootstrap-does)
- [Directory Layout](#directory-layout)
- [Shell Aliases (`ht-*`)](#shell-aliases-ht-)
- [Configuration](#configuration)
- [Auto-Update](#auto-update)
- [Manual Installation](#manual-installation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

**hacker-tool** is a Python-based security/utility toolkit designed to run natively on Android via **Termux** as well as standard Linux and macOS environments. The CAT-style bootstrap script (`bootstrap.sh`) handles the full environment setup in one shot — clone, deps, global command linking, GitHub remote configuration, auto-update scheduling, and health checks.

---

## Requirements

| Dependency | Minimum | Notes |
|-----------|---------|-------|
| `git` | any | Required — bootstrap will abort without it |
| `python3` | 3.9+ | 3.13 recommended |
| `pip` | any | Bundled with Python 3.9+ |
| `node` | 18+ | Optional — only needed for JS modules |
| `npm` | any | Optional — paired with node |
| `curl` | any | Optional — used by some modules |
| `jq` | any | Optional — JSON parsing in helpers |
| `bash` | 4.0+ | Required to run `bootstrap.sh` |

### Termux-specific
```bash
pkg update && pkg upgrade
pkg install git python nodejs curl bash
pkg install jq          # optional but recommended
```

---

## Quick Start — One-Command Bootstrap

**With SSH (recommended):**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/K1LLLAGT/hacker-tool/main/bootstrap.sh)
```

**Or clone first:**
```bash
git clone git@github.com:K1LLLAGT/hacker-tool.git
cd hacker-tool
bash bootstrap.sh
```

**With your username pre-set (skips the prompt):**
```bash
K1LLLAGT=K1LLLAGT bash bootstrap.sh
```

After bootstrap completes, reload your shell:
```bash
source ~/.bashrc   # bash
# or
source ~/.zshrc    # zsh
```

---

## Termux / Android Setup

Termux requires a few extra steps before bootstrapping because it uses a non-standard filesystem layout.

### 1. Storage permission
```bash
termux-setup-storage
```

### 2. Install dependencies
```bash
pkg update && pkg upgrade -y
pkg install git python nodejs curl bash jq openssh -y
```

### 3. Set up SSH key for GitHub (optional but recommended)
```bash
ssh-keygen -t ed25519 -C "K1LLLAGT" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
# Add the output to https://github.com/settings/ssh/new
ssh -T git@github.com   # verify connection
```

> **Without an SSH key** the bootstrap automatically falls back to HTTPS — no action needed.

### 4. Run the bootstrap
```bash
git clone https://github.com/K1LLLAGT/hacker-tool.git
cd hacker-tool
bash bootstrap.sh
```

### Known Termux quirks handled by bootstrap

| Issue | Root Cause | How bootstrap handles it |
|-------|-----------|--------------------------|
| `/tmp` permission denied | Termux mounts no global `/tmp` | Uses `$TMPDIR` (`/data/data/com.termux/files/usr/tmp`) with `~/tmp` fallback |
| `git fsck` shallow warnings | Bootstrap clones with `--depth 1` | Detects shallow repo and skips `fsck` gracefully |
| `~/.local/bin` not in PATH | Termux `.bashrc` starts minimal | Bootstrap injects `export PATH` line automatically |
| No `cron` daemon | Termux doesn't ship crond | Auto-update script is written; use `termux-job-scheduler` or Termux:Boot to invoke it |
| busybox `sed` limitations | Pipes inside `s|||` replacement fail | Use Python3 for multi-line patches (see [Troubleshooting](#troubleshooting)) |

### Termux auto-update via Termux:Boot

Install the **Termux:Boot** app, then:
```bash
mkdir -p ~/.termux/boot
ln -sf ~/.local/share/hacker-tool/scripts/auto-update.sh ~/.termux/boot/ht-update.sh
```
This runs the auto-updater every time Termux starts.

---

## What the Bootstrap Does

The script runs **10 steps** with full colour output, auto-stash safety, and a health check report:

```
STEP  1/10   Pre-flight checks          — validates git, python, node, curl, jq
STEP  2/10   Clone / Update repository  — SSH-first with HTTPS fallback; auto-stash on re-run
STEP  3/10   Install dependencies       — npm ci, pip + venv, make deps (whichever apply)
STEP  4/10   Link global commands       — npm link + bin/ symlinks → ~/.local/bin
STEP  5/10   Configure GitHub remote    — SSH vs HTTPS auto-select, pull.rebase, upstream tracking
STEP  6/10   Create config              — writes ~/.config/hacker-tool/config.toml
STEP  7/10   Install auto-update        — writes scripts/auto-update.sh + registers cron/launchd
STEP  8/10   Write shell aliases        — writes aliases.sh, sources it from your shell RC
STEP  9/10   Final health checks        — 8-point integrity scan with pass/warn/fail tally
STEP 10/10   Final report               — summary of errors, warnings, and skipped steps
```

### Auto-stash logic (Steps 2 & 7)

On every run against an existing repo, the bootstrap and the auto-updater:

1. Detect uncommitted changes with `git status --porcelain`
2. Stash them as `bootstrap-autostash-YYYYMMDD-HHMMSS`
3. Pull with `--ff-only`; falls back to `rebase` if fast-forward fails
4. Re-apply the stash with `git stash pop`
5. If stash conflicts occur, the stash is left intact with a warning (not lost)

---

## Directory Layout

After bootstrap your environment looks like this:

```
~/.local/share/hacker-tool/    ← INSTALL_DIR  (repo clone)
├── scripts/
│   └── auto-update.sh         ← auto-updater with stash logic
├── logs/
│   └── auto-update-YYYYMMDD.log
├── .venv/                     ← Python virtualenv
├── bootstrap.sh
├── requirements.txt
└── ...

~/.config/hacker-tool/         ← CONFIG_DIR
├── config.toml                ← main config (edit freely)
└── aliases.sh                 ← shell aliases (sourced from .bashrc)

~/.local/bin/                  ← BIN_DIR (on PATH after reload)
└── hacker-tool                ← launcher stub → INSTALL_DIR entry point
```

---

## Shell Aliases (`ht-*`)

All aliases are written to `~/.config/hacker-tool/aliases.sh` and automatically sourced from your shell RC.

| Alias | Expands to | Purpose |
|-------|-----------|---------|
| `ht` | `~/.local/bin/hacker-tool` | Run the tool |
| `ht-update` | `~/.local/share/hacker-tool/scripts/auto-update.sh` | Manually trigger an update |
| `ht-log` | `tail -f .../logs/auto-update-YYYYMMDD.log` | Live-tail today's update log |
| `ht-config` | `$EDITOR ~/.config/hacker-tool/config.toml` | Edit the config in your preferred editor |
| `ht-status` | `cd INSTALL_DIR && git status && git log --oneline -5` | Quick repo health glance |

**Re-source aliases at any time:**
```bash
source ~/.config/hacker-tool/aliases.sh
```

---

## Configuration

The bootstrap auto-generates `~/.config/hacker-tool/config.toml`:

```toml
[general]
install_dir    = "~/.local/share/hacker-tool"
bin_dir        = "~/.local/bin"
auto_update    = true
update_channel = "main"     # main | dev | nightly
log_level      = "info"     # debug | info | warn | error

[github]
username = "K1LLLAGT"
remote   = "git@github.com:K1LLLAGT/hacker-tool.git"
https    = "https://github.com/K1LLLAGT/hacker-tool.git"

[update]
schedule     = "0 */6 * * *"   # every 6 hours
auto_stash   = true
stash_prefix = "bootstrap-autostash"
on_conflict  = "warn"           # warn | abort | force
```

Edit with `ht-config` or directly with `nano ~/.config/hacker-tool/config.toml`.

---

## Auto-Update

The updater script at `~/.local/share/hacker-tool/scripts/auto-update.sh` runs automatically every 6 hours (via cron on Linux/macOS, or Termux:Boot on Android).

**Manual update:**
```bash
ht-update
```

**Watch the live log:**
```bash
ht-log
```

**Update flow:**
1. `git fetch --all --prune`
2. Compare local vs remote HEAD
3. Auto-stash dirty working tree if needed
4. `git pull --ff-only` → fallback to `git rebase`
5. Re-apply stash
6. Re-run `npm ci` if `package.json` changed
7. Re-run `pip install -r requirements.txt` if `requirements.txt` changed

---

## Manual Installation

If you prefer not to use the bootstrap script:

```bash
# 1. Clone
git clone https://github.com/K1LLLAGT/hacker-tool.git
cd hacker-tool

# 2. Python venv + deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run directly
python3 main.py --help
```

---

## Troubleshooting

### `ht: command not found` after sourcing `.bashrc`
```bash
# Check alias file is sourced
grep hacker-tool ~/.bashrc

# Re-source manually
source ~/.config/hacker-tool/aliases.sh

# Verify launcher exists
ls -la ~/.local/bin/hacker-tool
```

### `bash: ~/.local/bin/hacker-tool: No such file or directory`
The launcher stub wasn't created (repo has no `bin/` directory). Create it:
```bash
cat > ~/.local/bin/hacker-tool << 'STUB'
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/hacker-tool"
PYTHON="$INSTALL_DIR/.venv/bin/python3"
for entry in cli.py main.py __main__.py; do
  [[ -f "$INSTALL_DIR/$entry" ]] && exec "$PYTHON" "$INSTALL_DIR/$entry" "$@"
done
echo "No entry point found. Files:"; ls "$INSTALL_DIR"; exit 1
STUB
chmod +x ~/.local/bin/hacker-tool
```

### `git fsck` warnings on fresh clone
Expected on shallow clones (`--depth 1`). Not a real error — the bootstrap v2.0.0+ detects and skips fsck for shallow repos automatically.

### `/tmp: Permission denied` (Termux)
Upgrade to bootstrap v2.0.0+ which uses `$TMPDIR` instead of `/tmp`. Or patch manually:
```bash
sed -i 's|LOG_FILE="/tmp/|_TMPBASE="${TMPDIR:-$HOME/tmp}"; mkdir -p "$_TMPBASE"; LOG_FILE="${_TMPBASE}/|' bootstrap.sh
```

### `sed` fails on complex patterns (Termux busybox)
Termux's `sed` doesn't support pipes inside replacement strings. Use Python3 instead:
```bash
python3 -c "
with open('bootstrap.sh','r') as f: c=f.read()
# apply your substitution to string c here
with open('bootstrap.sh','w') as f: f.write(c)
"
```

### `jq not found`
```bash
pkg install jq      # Termux
# or
sudo apt install jq # Debian/Ubuntu
```

---

## Contributing

```bash
# Fork → clone your fork
git clone git@github.com:YOUR_USERNAME/hacker-tool.git
cd hacker-tool

# Create a feature branch
git checkout -b feature/your-feature

# Make changes, then push
git push origin feature/your-feature

# Open a Pull Request against K1LLLAGT/hacker-tool:main
```

---

<div align="center">
<sub>Built on Android · Termux · aarch64 · by K1LLLAGT</sub>
</div>
