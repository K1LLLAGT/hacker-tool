# Changelog

All notable changes to **hacker-tool** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

## [1.0.0] — 2026-07-04

### Added
- Initial repository scaffold
- `requirements.txt` with Python dependencies
- Python virtualenv setup

---

[Unreleased]: https://github.com/K1LLLAGT/hacker-tool/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/K1LLLAGT/hacker-tool/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/K1LLLAGT/hacker-tool/releases/tag/v1.0.0
