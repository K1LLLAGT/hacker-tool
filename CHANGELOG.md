# Changelog

All notable changes to **hacker-tool** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] — 2026-07-04

### Added — Offline Data Bundles
- **`data/oui.json`** — 649 IEEE OUI to vendor mappings
- **`data/cve.json`** — 125 CVEs across 34 ports, CVSS scores + risk flags
- **`data/defaultcreds.json`** — 164 default credential entries, 50+ vendors

### Added — `vuln/` new verb
- `vuln cve port <N>` — offline port-to-CVE lookup with CVSS ranking
- `vuln cve service <name>` — CVE index by service keyword
- `vuln cve list` — all 34 indexed ports with max CVSS
- `vuln defaultcreds <keyword>` — vendor/device/protocol credential search
- `vuln portrisk [ports]` — exposure risk scoring 0-100 with letter grade
- `vuln ciphers <ssl_audit.json>` — deprecated TLS cipher/protocol detector

### Added — `net/pipeline`
- `net pipeline <target>` — runs nmap scan then auto-matches open ports
  against `cve.json` and `defaultcreds.json`; prints risk summary
- `--top-ports N` — configurable scan depth (default 100)
- `--save` — writes full JSON report to `reports/pipeline_<target>_<ts>.json`
- `--notify` — sends Termux notification on completion

### Changed
- `scripts/completions.bash` — all 10 verbs + full sub-command trees

---

## [2.2.0] — 2026-07-04

### Added
- **`clean` command** (`clean.py`) — removes `.pyc` files and `__pycache__`
  dirs recursively; `--dry-run` preview mode; `--path` to scope to a subtree.
  Stdlib-only, no external dependencies.
- **`crypto` verb** — offline cryptographic utilities: `hash` (sha256/sha1/
  md5/sha512/sha224/sha384), `encode`/`decode` (base64 + URL-safe variant),
  `entropy` (Shannon entropy with encryption-detection verdict), `compare`
  (constant-time digest comparison via `hmac.compare_digest`).
- **`device` verb** — Android/Termux device introspection: `info` (getprop),
  `storage` (df), `battery` (/sys/class/power_supply), `net` (ip addr + IPv6),
  `cpu` (/proc/cpuinfo + cpufreq scaling). Offline-only, stdlib-only.
- **`vuln` verb** — vulnerability surface checks: `headers` (HTTP security
  header audit with A–F grade; online, opt-in), `ports` (TCP connect scan
  restricted to RFC1918/loopback with per-port CVE hints), `perms` (filesystem
  walk flagging world-writable, SUID, SGID files).
- **`proc` verb** — process inspection: `list`, `top` (sort by rss_kb/
  cpu_ticks/pid), `find`, `kill` (TERM/KILL/HUP/INT), `mem` (/proc/meminfo
  summary). Reads /proc directly — no `ps` binary required.
- **`hacker-tool.py`** — all four new verbs wired into `build_parser()` and
  `main()` dispatch; docstring updated with full usage for all 27 subcommands.
- **`ht_launcher.py` TUI** — 20 new COMMANDS entries; 4 new top-level submenus
  (Crypto, Device, Vuln, Proc); `prompt_choice()` constrained-input helper;
  13 new token handlers (algo, b64, hash_a/b, text, file/path/root, url,
  host, ports, pid, sig, n, sort, filter/name).
- **`scripts/completions.bash`** — bash tab-completion for `htctl` and
  `hacker-tool`/`hacker-tool.py`; all verbs, subcommands, flags; constrained
  cycling for --algo/--sig/--sort/--fmt; path completion for --file/--root/
  --out; live PID completion for `proc kill <Tab>`. No bash-completion package
  required — Termux-safe fallback included.
- **`htctl`** — added `crypto`, `device`, `vuln`, `proc` pass-through cases
  alongside existing `clean` and `fix-scan`.

### Fixed
- **Tier 2 — dual-copy drift**: merged `.gitignore` (combined SSH-key rules
  from Termux copy + workspace/audit-backup rules from storage copy); ported
  hardcoded `/data/data/com.termux/...` paths in `config.yml` and
  `ht_launcher.py` to portable `~` expansion; rsync'd both copies to parity.

### Security
- Deleted `.ssh/id_ed25519` private key from `/storage/emulated/0/` after
  rsync accidentally pushed `.ssh/` to Android shared storage (readable by
  any app with READ_EXTERNAL_STORAGE). Added `--exclude='.ssh/'` to all
  rsync invocations to prevent recurrence.
- `vuln ports` and `net scan` both enforce RFC1918/loopback-only policy;
  public IPs raise `ValueError` before any socket is opened.
- `htctl clean` scoped to project tree only; `--dry-run` default recommended
  for first-time runs in new directories.

## [Unreleased]

---

## [2.1.0] — 2026-07-04

### Fixed — Tier 1 (Breaks Right Now)
- **#1 Install directory** — `INSTALL_DIR` already correctly set to `$HOME/${REPO_NAME}`
  in bootstrap.sh; confirmed no stale clone at `~/.local/share/hacker-tool`
- **#2 Launcher stub** — `~/.local/bin/hacker-tool` rewritten to target
  `hacker-tool.py` directly; auto-selects venv Python when available
- **#3 `ht` alias collision** — `aliases.sh` unified so both bootstrap and
  `htctl link` register `ht → ht_launcher.py`; no more last-write-wins conflict
- **#4 Config path mismatch** — `config.toml` `install_dir` corrected to
  `~/hacker-tool`; `config.yml` absolute Termux paths replaced with `~` equivalents
- **#5 Missing `VERSION` file** — `VERSION` file created with `2.0.0`;
  `htctl version` no longer errors
- **#6 Hardcoded `TOOL` path** — `ht_launcher.py` `TOOL` list now uses
  `os.path.dirname(__file__)` + `sys.executable`; survives any clone location

### Fixed — Tier 2 (Silent Failures)
- **#7 Competing update systems** — `auto-update.sh` now delegates to
  `htctl update` when available; falls back to raw git only when htctl absent;
  eliminates double-stash races
- **#8 Dead cron on Termux** — cron registration replaced with a
  `~/.termux/boot/ht-update.sh` hook; auto-updater now actually runs on device boot
- **#9 Always-firing username prompt** — `main()` guard in `bootstrap.sh`
  no longer prompts when `K1LLLAGT` is already hardcoded; cleaned to a single info line
- **#10 Orphaned `fix_main.py`** — wired into `htctl` as `htctl fix-scan`
- **#11 Orphaned `clean.py`** — wired into `htctl` as `htctl clean`
- **#12 `reports/` in git** — added to `.gitignore`; generated scan reports
  with sensitive network data can no longer be accidentally committed
- **#13 `.venv/` in git** — added to `.gitignore` alongside `__pycache__/`,
  `*.pyc`, `.mypy_cache/`

### Fixed — Tier 3 (Security & Technical Debt)
- **#14 Plaintext SMB credentials** — new `core/secrets.py` provides a
  symmetric XOR-encrypted store at `~/.config/hacker-tool/.secrets`; exposed via
  `htctl secrets set|get|list|delete`; key stored at `~/.config/hacker-tool/.key` (chmod 600)
- **#15 No audit trail** — `_write_session_log()` added to `cli.py`; every
  dispatched command appends a timestamped line to `logs/session.log`
- **#16 Monolithic requirements** — runtime deps remain in `requirements.txt`
  (`pyyaml`, `requests`, `beautifulsoup4`); dev-only deps (`pytest`, `mypy`,
  `ruff`) moved to new `requirements-dev.txt`; `htctl deps --dev` installs both

### Fixed — Tier 4 (Docs & Polish)
- **#17 README path conflicts** — all `~/.local/share/hacker-tool` references
  corrected to `~/hacker-tool`; bootstrap and tool now agree on install location
- **#18 `REQUIREMENTS.md` unlisted** — added to README Table of Contents as
  a direct link to `./REQUIREMENTS.md`
- **#19 Inaccurate `v1.0.0` entry** — CHANGELOG v1.0.0 block rewritten to
  accurately reflect the full codebase present at that tag: 6 CLI verb modules,
  9-file test suite, `htctl`, `ht_launcher.py`, `bootstrap-termux.sh`, docs, workspaces,
  audit-backup system, `mypy.ini`
- **#20 No GitHub Releases** — `v1.0.0`, `v2.0.0`, and `v2.1.0` published
  on GitHub Releases with CHANGELOG notes; `v2.1.0` set as latest
- **#21 No tab completion** — `scripts/completions.bash` generated with
  full sub-command trees for `ht`, `ht-cli`, `hackertool`, and `htctl`;
  auto-sourced from `.bashrc`; `htctl secrets` sub-completions included
- **#22 `STEP 10/9` + `git fsck`** — `TOTAL_STEPS` corrected to `10`;
  `git fsck` patched to detect shallow clones and skip gracefully

### Fixed — Post-Tier hotfix
- **`HT_ROOT` unbound in `htctl`** — injected subcommand blocks (`clean`,
  `fix-scan`, `secrets`, `deps`) used wrong variable `$HT_ROOT`; corrected to
  `$HT_DIR` which is the variable defined at line 17 of `htctl`

### Security
- `id_ed25519*`, `*.pub`, `.ssh/`, `*.pem`, `*.key`, `hacker-tool*.txt`,
  `data/*.log` added to `.gitignore` — SSH key material and tree dump files
  can no longer be accidentally tracked or pushed

---

## [2.0.0] — 2026-07-04

### Added
- **CAT-style bootstrap script** (`bootstrap.sh`) — full 10-step environment
  setup with colour output, braille spinner, and per-step pass/warn/fail tracking
- **Auto-stash logic** — detects dirty working tree before every pull,
  stashes as `bootstrap-autostash-YYYYMMDD-HHMMSS`, restores after merge;
  leaves stash intact on conflict instead of silently dropping changes
- **Auto-update daemon** (`scripts/auto-update.sh`) — registered via cron
  (Linux/macOS) and launchd plist (macOS); Termux:Boot compatible
- **Shell alias suite** — `ht`, `ht-update`, `ht-log`, `ht-config`,
  `ht-status` written to `~/.config/hacker-tool/aliases.sh` and
  auto-sourced from shell RC
- **TOML config** — auto-generated at `~/.config/hacker-tool/config.toml`
  with update channel, log level, stash prefix, and conflict policy
- **8-point health check** — repo integrity, remote URL, node_modules,
  Python venv, broken symlinks, updater executable bit, config presence,
  cron registration
- **SSH → HTTPS fallback** — bootstrap detects ssh-agent availability and
  selects the appropriate remote automatically
- **Termux / Android support** — uses `$TMPDIR` instead of `/tmp`,
  handles busybox `sed` limitations, PATH injection into `.bashrc`
- **Smart launcher stub** — `~/.local/bin/hacker-tool` probes multiple
  Python entry points (`cli.py`, `main.py`, `__main__.py`, package module)
- **README.md** — full documentation covering bootstrap, Termux setup,
  all aliases, config reference, auto-update flow, and troubleshooting

### Fixed
- `STEP 10/9` counter overflow — `TOTAL_STEPS` corrected to `10`
- `git fsck` false-positive warnings on shallow clones (`--depth 1`) —
  bootstrap detects shallow repos and skips fsck gracefully
- `/tmp` permission denied on Termux — log path now resolves via
  `${TMPDIR:-$HOME/tmp}` with `mkdir -p` guard

### Changed
- `GITHUB_USERNAME` variable renamed to `K1LLLAGT` to match repo owner
- Default remote preference is SSH with automatic HTTPS fallback
- `pull.rebase=true` and `push.default=current` set globally on clone

---

## [1.0.0] — 2026-07-03

### Added
- **Core architecture** — `hacker-tool.py` entry point, `cli.py` dispatcher,
  `core/config.py`, `core/storage.py`, `core/logging_setup.py`
- **6 CLI verb modules** — `fs/manifest.py`, `net/scan.py`, `web/checks.py`,
  `project/snapshot.py`, `sync/commands.py`, `report/generate.py`
- **Full test suite** — 9 test files in `tests/` covering every module
- **Module docs** — `docs/` with per-module Markdown references
- **`htctl` manager** — `deps`, `doctor`, `update`, `backup`, `test`, `edit`,
  `link`, `clean`, `fix-scan` subcommands
- **`ht_launcher.py`** — CAT-style TUI launcher
- **`bootstrap-termux.sh`** — Termux/Ubuntu-native bootstrap
- **`config.yml`** — YAML config with workspace, SMB, and logging settings
- **`requirements.txt`** — runtime deps: pyyaml, requests, beautifulsoup4
- **`mypy.ini`** — type-checking config
- **`workspaces/`** — local + remote workspace directories with `.gitkeep`
- **`.audit-backups/`** — automated backup system via `hacker_tool_audit.py`

---

[Unreleased]: https://github.com/K1LLLAGT/hacker-tool/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/K1LLLAGT/hacker-tool/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/K1LLLAGT/hacker-tool/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/K1LLLAGT/hacker-tool/releases/tag/v1.0.0
