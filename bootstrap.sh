#!/usr/bin/env bash
# ==============================================================================
#  ██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗       ████████╗ ██████╗  ██████╗ ██╗
#  ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗      ╚══██╔══╝██╔═══██╗██╔═══██╗██║
#  ███████║███████║██║     █████╔╝ █████╗  ██████╔╝─────    ██║   ██║   ██║██║   ██║██║
#  ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗         ██║   ██║   ██║██║   ██║██║
#  ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║         ██║   ╚██████╔╝╚██████╔╝███████╗
#  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝         ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
#
#  Bootstrap Script  v2.0.0  |  CAT-Style  |  by Greg
#  Repository  : https://github.com/K1LLLAGT/hacker-tool
#  Description : Full environment bootstrap — clone, deps, link, remote,
#                auto-update with stash, and final health checks.
# ==============================================================================

set -euo pipefail
IFS=$'\n\t'

# ── Colour palette ─────────────────────────────────────────────────────────────
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"

BLACK="\033[30m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"
WHITE="\033[37m"

BG_BLACK="\033[40m"
BG_RED="\033[41m"
BG_GREEN="\033[42m"
BG_BLUE="\033[44m"
BG_MAGENTA="\033[45m"
BG_CYAN="\033[46m"

# ── Configuration (edit these) ─────────────────────────────────────────────────
REPO_NAME="hacker-tool"
K1LLLAGT="${K1LLLAGT:-K1LLLAGT}"
GITHUB_REMOTE="git@github.com:${K1LLLAGT}/${REPO_NAME}.git"
GITHUB_HTTPS="https://github.com/${K1LLLAGT}/${REPO_NAME}.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/${REPO_NAME}}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.config/${REPO_NAME}}"
_TMPBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_TMPBASE"
LOG_FILE="${_TMPBASE}/${REPO_NAME}-bootstrap-$(date +%Y%m%d-%H%M%S).log"
UPDATE_CRON_SCHEDULE="0 */6 * * *"   # every 6 hours
NODE_MIN_VERSION=18
PYTHON_MIN_VERSION="3.9"

# ── Runtime state ──────────────────────────────────────────────────────────────
ERRORS=()
WARNINGS=()
SKIPPED=()
STEP=0
TOTAL_STEPS=10

# ══════════════════════════════════════════════════════════════════════════════
#  PRETTY-PRINT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_ruler() {
  printf "${DIM}${CYAN}%s${RESET}\n" \
    "──────────────────────────────────────────────────────────────────────────────"
}

_banner() {
  clear
  printf "\n"
  printf "${BOLD}${CYAN}"
  cat << 'CATBANNER'
   /\_____/\
  /  o   o  \     H A C K E R - T O O L   B O O T S T R A P
 ( ==  ^  == )    ─────────────────────────────────────────
  )         (     CAT-Style • Auto-stash • Health Checks
 (           )
  \  |   |  /
 _.|___|___| _
CATBANNER
  printf "${RESET}\n"
  _ruler
  printf "  ${DIM}Log  →  ${LOG_FILE}${RESET}\n"
  printf "  ${DIM}Repo →  ${GITHUB_REMOTE}${RESET}\n"
  printf "  ${DIM}Dest →  ${INSTALL_DIR}${RESET}\n"
  _ruler
  printf "\n"
}

_step() {
  (( STEP++ )) || true
  local label="$1"
  printf "\n${BOLD}${BG_BLUE}${WHITE}  STEP %d/%d  ${RESET}${BOLD}${BLUE}  %s${RESET}\n" \
    "$STEP" "$TOTAL_STEPS" "$label"
  _ruler
}

_ok()   { printf "  ${GREEN}✔${RESET}  %s\n" "$1"; }
_info() { printf "  ${CYAN}ℹ${RESET}  %s\n"  "$1"; }
_warn() { printf "  ${YELLOW}⚠${RESET}  %s\n" "$1"; WARNINGS+=("$1"); }
_skip() { printf "  ${MAGENTA}↷${RESET}  %s ${DIM}(skipped)${RESET}\n" "$1"; SKIPPED+=("$1"); }
_fail() { printf "  ${RED}✘${RESET}  %s\n" "$1"; ERRORS+=("$1"); }
_die()  {
  printf "\n${BOLD}${BG_RED}${WHITE}  FATAL  ${RESET}${BOLD}${RED}  %s${RESET}\n\n" "$1"
  exit 1
}

# ── Spinner ────────────────────────────────────────────────────────────────────
_spin() {
  local pid=$1 msg="${2:-Working…}"
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r  ${CYAN}${spin:$((i % ${#spin})):1}${RESET}  ${DIM}%s${RESET}" "$msg"
    (( i++ )) || true
    sleep 0.1
  done
  printf "\r%-60s\r" " "
}

# ── Run a command silently, log everything ─────────────────────────────────────
_run() {
  local desc="$1"; shift
  printf "  ${DIM}▶ %s${RESET}\n" "$desc"
  if "$@" >>"$LOG_FILE" 2>&1; then
    _ok "$desc"
    return 0
  else
    _fail "$desc  (exit $?)"
    return 1
  fi
}

# ── Require a binary on PATH ───────────────────────────────────────────────────
_require() {
  local bin="$1" hint="${2:-}"
  if command -v "$bin" &>/dev/null; then
    _ok "$bin found at $(command -v "$bin")"
    return 0
  else
    if [[ -n "$hint" ]]; then
      _fail "$bin not found — $hint"
    else
      _fail "$bin not found"
    fi
    return 1
  fi
}

# ── Version comparison (semver-ish) ───────────────────────────────────────────
_ver_gte() {
  printf '%s\n%s\n' "$2" "$1" | sort -t. -k1,1n -k2,2n -k3,3n | head -1 | grep -qF "$2"
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 0 — PRE-FLIGHT
# ══════════════════════════════════════════════════════════════════════════════
preflight() {
  _step "Pre-flight checks"

  OS="$(uname -s)"
  ARCH="$(uname -m)"
  _info "System: ${OS} / ${ARCH}"

  _require git "Install git: https://git-scm.com" || _die "git is required."

  if _require node; then
    NODE_VER="$(node -e 'process.stdout.write(process.versions.node)')"
    _info "Node version: ${NODE_VER}"
    if ! _ver_gte "$NODE_VER" "${NODE_MIN_VERSION}.0.0"; then
      _warn "Node ${NODE_MIN_VERSION}+ recommended (found ${NODE_VER})"
    fi
    _require npm
  else
    _warn "Node.js not found — JS dependencies will be skipped"
  fi

  PYTHON_BIN=""
  for py in python3 python; do
    if command -v "$py" &>/dev/null && "$py" -c 'import sys; sys.exit(0 if sys.version_info>=(3,0) else 1)' 2>/dev/null; then
      PYTHON_BIN="$py"
      PY_VER="$("$py" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
      _ok "Python ${PY_VER} at $(command -v "$py")"
      if ! _ver_gte "$PY_VER" "$PYTHON_MIN_VERSION"; then
        _warn "Python ${PYTHON_MIN_VERSION}+ recommended (found ${PY_VER})"
      fi
      break
    fi
  done
  [[ -z "$PYTHON_BIN" ]] && _warn "Python 3 not found — Python deps will be skipped"

  if command -v curl &>/dev/null;  then _ok "curl found"; else _warn "curl not found"; fi
  if command -v jq   &>/dev/null;  then _ok "jq found";   else _warn "jq not found (JSON parsing limited)"; fi

  mkdir -p "$BIN_DIR"
  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    _warn "${BIN_DIR} not in PATH — will attempt to add it"
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — CLONE OR UPDATE REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════
clone_or_update() {
  _step "Clone / Update repository"

  mkdir -p "$(dirname "$INSTALL_DIR")"

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    _info "Repository already exists at ${INSTALL_DIR}"
    _info "Pulling latest changes with auto-stash…"
    (
      cd "$INSTALL_DIR"
      STASH_MSG="bootstrap-autostash-$(date +%Y%m%d-%H%M%S)"
      DIRTY="$(git status --porcelain 2>/dev/null)"

      if [[ -n "$DIRTY" ]]; then
        _warn "Uncommitted changes detected — stashing as '${STASH_MSG}'"
        git stash push -u -m "$STASH_MSG" >>"$LOG_FILE" 2>&1
        STASHED=true
      else
        STASHED=false
      fi

      git fetch --all --prune >>"$LOG_FILE" 2>&1
      CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'HEAD')"
      git pull --ff-only origin "$CURRENT_BRANCH" >>"$LOG_FILE" 2>&1 || {
        _warn "Fast-forward failed; attempting rebase…"
        git rebase origin/"$CURRENT_BRANCH" >>"$LOG_FILE" 2>&1 || {
          _fail "Rebase failed — manual intervention required."
          git rebase --abort >>"$LOG_FILE" 2>&1 || true
        }
      }

      if [[ "$STASHED" == true ]]; then
        if git stash pop >>"$LOG_FILE" 2>&1; then
          _ok "Stash '${STASH_MSG}' restored cleanly"
        else
          _warn "Stash restore had conflicts — stash left in place as '${STASH_MSG}'"
        fi
      fi
    )
    _ok "Repository updated"

  else
    _info "Cloning ${REPO_NAME} into ${INSTALL_DIR}…"
    if git clone --depth 1 "$GITHUB_REMOTE" "$INSTALL_DIR" >>"$LOG_FILE" 2>&1; then
      _ok "Cloned via SSH"
    else
      _warn "SSH clone failed — retrying with HTTPS"
      git clone --depth 1 "$GITHUB_HTTPS" "$INSTALL_DIR" >>"$LOG_FILE" 2>&1 \
        && _ok "Cloned via HTTPS" \
        || _die "Clone failed via both SSH and HTTPS. Check credentials and repo URL."
    fi
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — INSTALL DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════
install_deps() {
  _step "Install dependencies"

  cd "$INSTALL_DIR"

  # ── Node / npm ────────────────────────────────────────────────────────────
  if command -v npm &>/dev/null && [[ -f package.json ]]; then
    _info "Installing Node dependencies (npm ci)…"
    if npm ci --prefer-offline >>"$LOG_FILE" 2>&1; then
      _ok "npm ci succeeded"
    else
      _info "npm ci failed — falling back to npm install"
      npm install >>"$LOG_FILE" 2>&1 && _ok "npm install succeeded" \
        || _warn "npm install returned errors — check ${LOG_FILE}"
    fi
  elif [[ ! -f package.json ]]; then
    _skip "No package.json — skipping npm"
  fi

  # ── Python / pip ──────────────────────────────────────────────────────────
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if [[ -f requirements.txt ]]; then
      _info "Installing Python dependencies (pip)…"
      if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        if "$PYTHON_BIN" -m venv .venv >>"$LOG_FILE" 2>&1; then
          _ok "Created virtualenv at .venv"
          # shellcheck disable=SC1091
          source .venv/bin/activate
        else
          _warn "venv creation failed — installing into user site"
        fi
      fi
      "$PYTHON_BIN" -m pip install --upgrade pip >>"$LOG_FILE" 2>&1 || true
      "$PYTHON_BIN" -m pip install -r requirements.txt >>"$LOG_FILE" 2>&1 \
        && _ok "Python requirements installed" \
        || _warn "pip install had errors — check ${LOG_FILE}"
    else
      _skip "No requirements.txt — skipping pip"
    fi

    if [[ -f pyproject.toml ]] || [[ -f setup.py ]]; then
      _info "Running editable install (pip install -e .)…"
      "$PYTHON_BIN" -m pip install -e . >>"$LOG_FILE" 2>&1 \
        && _ok "Editable install succeeded" \
        || _warn "Editable install failed — check ${LOG_FILE}"
    fi
  fi

  # ── Makefile targets ──────────────────────────────────────────────────────
  if command -v make &>/dev/null && [[ -f Makefile ]]; then
    if grep -q '^deps\b\|^install-deps\b' Makefile 2>/dev/null; then
      _info "Running Makefile deps target…"
      TARGET=$(grep -oE '^(deps|install-deps)' Makefile | head -1)
      make "$TARGET" >>"$LOG_FILE" 2>&1 \
        && _ok "make ${TARGET} succeeded" \
        || _warn "make ${TARGET} returned errors"
    fi
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — LINK GLOBAL COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
link_globals() {
  _step "Link global commands"

  cd "$INSTALL_DIR"
  mkdir -p "$BIN_DIR"

  # ── npm link ──────────────────────────────────────────────────────────────
  if command -v npm &>/dev/null && [[ -f package.json ]]; then
    if grep -q '"bin"' package.json 2>/dev/null; then
      _info "Linking npm binaries…"
      npm link >>"$LOG_FILE" 2>&1 \
        && _ok "npm link succeeded" \
        || _warn "npm link failed — you may need sudo or a local-bin npm prefix"
    else
      _skip "No 'bin' key in package.json"
    fi
  fi

  # ── Symlink scripts in bin/ ───────────────────────────────────────────────
  if [[ -d "$INSTALL_DIR/bin" ]]; then
    for script in "$INSTALL_DIR"/bin/*; do
      [[ -f "$script" ]] || continue
      local name
      name="$(basename "$script")"
      local target="${BIN_DIR}/${name}"
      chmod +x "$script"
      if [[ -L "$target" ]] && [[ "$(readlink -f "$target")" == "$(readlink -f "$script")" ]]; then
        _skip "Already linked: ${name}"
      else
        ln -sf "$script" "$target" \
          && _ok "Linked: ${target} → ${script}" \
          || _warn "Could not link ${name}"
      fi
    done
  fi

  # ── Shell profile PATH injection ──────────────────────────────────────────
  SHELL_RC=""
  case "${SHELL:-}" in
    */zsh)  SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="${HOME}/.bashrc" ;;
    *)      SHELL_RC="${HOME}/.profile" ;;
  esac

  if [[ -n "$SHELL_RC" ]]; then
    PATH_EXPORT="export PATH=\"\$PATH:${BIN_DIR}\""
    if ! grep -qF "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
      printf '\n# Added by hacker-tool bootstrap\n%s\n' "$PATH_EXPORT" >> "$SHELL_RC"
      _ok "PATH injection added to ${SHELL_RC}"
    else
      _skip "${BIN_DIR} already in ${SHELL_RC}"
    fi
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — CONFIGURE GITHUB REMOTE
# ══════════════════════════════════════════════════════════════════════════════
configure_remote() {
  _step "Configure GitHub remote"

  cd "$INSTALL_DIR"

  CURRENT_REMOTE="$(git remote get-url origin 2>/dev/null || echo '')"

  if ssh-add -l &>/dev/null || ssh-add -l 2>&1 | grep -q 'no identities'; then
    PREFERRED_REMOTE="$GITHUB_REMOTE"
    REMOTE_TYPE="SSH"
  else
    PREFERRED_REMOTE="$GITHUB_HTTPS"
    REMOTE_TYPE="HTTPS"
  fi

  if [[ -z "$CURRENT_REMOTE" ]]; then
    git remote add origin "$PREFERRED_REMOTE" >>"$LOG_FILE" 2>&1 \
      && _ok "Remote 'origin' set to ${PREFERRED_REMOTE} (${REMOTE_TYPE})" \
      || _warn "Could not set remote"
  elif [[ "$CURRENT_REMOTE" != "$PREFERRED_REMOTE" ]]; then
    _info "Current remote: ${CURRENT_REMOTE}"
    git remote set-url origin "$PREFERRED_REMOTE" >>"$LOG_FILE" 2>&1 \
      && _ok "Remote updated to ${PREFERRED_REMOTE} (${REMOTE_TYPE})" \
      || _warn "Could not update remote URL"
  else
    _ok "Remote 'origin' already correct: ${CURRENT_REMOTE}"
  fi

  git config pull.rebase true    >>"$LOG_FILE" 2>&1 && _ok "pull.rebase=true"
  git config push.default current >>"$LOG_FILE" 2>&1 && _ok "push.default=current"

  git fetch --all --prune >>"$LOG_FILE" 2>&1 \
    && _ok "Remote refs fetched" \
    || _warn "Fetch failed — network or auth issue"

  BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'main')"
  git branch --set-upstream-to=origin/"$BRANCH" "$BRANCH" >>"$LOG_FILE" 2>&1 \
    && _ok "Tracking: ${BRANCH} → origin/${BRANCH}" \
    || _warn "Could not set upstream (branch may not exist remotely yet)"
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — CREATE CONFIG DIRECTORY & DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════
create_config() {
  _step "Create config directory and defaults"

  mkdir -p "$CONFIG_DIR"

  CONFIG_FILE="${CONFIG_DIR}/config.toml"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" << TOML
# hacker-tool — auto-generated config
# Generated : $(date -u +"%Y-%m-%dT%H:%M:%SZ")

[general]
install_dir    = "${INSTALL_DIR}"
bin_dir        = "${BIN_DIR}"
auto_update    = true
update_channel = "main"     # main | dev | nightly
log_level      = "info"     # debug | info | warn | error

[github]
username = "${K1LLLAGT}"
remote   = "${GITHUB_REMOTE}"
https    = "${GITHUB_HTTPS}"

[update]
schedule     = "${UPDATE_CRON_SCHEDULE}"
auto_stash   = true
stash_prefix = "bootstrap-autostash"
on_conflict  = "warn"       # warn | abort | force
TOML
    _ok "Config written to ${CONFIG_FILE}"
  else
    _skip "Config already exists: ${CONFIG_FILE}"
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — AUTO-UPDATE WITH AUTO-STASH LOGIC
# ══════════════════════════════════════════════════════════════════════════════
install_autoupdate() {
  _step "Install auto-update with auto-stash"

  UPDATER_SCRIPT="${INSTALL_DIR}/scripts/auto-update.sh"
  mkdir -p "$(dirname "$UPDATER_SCRIPT")"

  cat > "$UPDATER_SCRIPT" << 'UPDATER'
#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  hacker-tool — Auto-Update with Auto-Stash
#  Invoked by cron or launchd.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${INSTALL_DIR}/logs"
LOG_FILE="${LOG_DIR}/auto-update-$(date +%Y%m%d).log"
STASH_PREFIX="bootstrap-autostash"

mkdir -p "$LOG_DIR"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════"
echo "  AUTO-UPDATE  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════"

cd "$INSTALL_DIR"

# 1. Fetch quietly
git fetch --all --prune --quiet

BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'main')"
LOCAL="$(git rev-parse @)"
REMOTE="$(git rev-parse @{u} 2>/dev/null || echo '')"
BASE="$(git merge-base @ @{u} 2>/dev/null || echo '')"

if [[ -z "$REMOTE" ]]; then
  echo "[SKIP] No upstream tracking branch set."
  exit 0
fi

if [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "[OK]   Already up-to-date."
  exit 0
fi

if [[ "$LOCAL" == "$BASE" ]]; then
  echo "[INFO] Updates available — pulling…"
else
  echo "[WARN] Diverged from upstream — manual review recommended."
  exit 1
fi

# 2. Auto-stash if dirty
DIRTY="$(git status --porcelain 2>/dev/null)"
STASHED=false
if [[ -n "$DIRTY" ]]; then
  STASH_MSG="${STASH_PREFIX}-$(date +%Y%m%d-%H%M%S)"
  echo "[INFO] Stashing local changes: ${STASH_MSG}"
  git stash push -u -m "$STASH_MSG"
  STASHED=true
fi

# 3. Pull
if git pull --ff-only --quiet origin "$BRANCH"; then
  echo "[OK]   Pull succeeded."
else
  echo "[WARN] Fast-forward failed — attempting rebase."
  if git rebase origin/"$BRANCH"; then
    echo "[OK]   Rebase succeeded."
  else
    echo "[FAIL] Rebase failed — aborting."
    git rebase --abort 2>/dev/null || true
    if [[ "$STASHED" == true ]]; then
      git stash pop || echo "[WARN] Stash pop failed after rebase abort."
    fi
    exit 1
  fi
fi

# 4. Re-apply stash
if [[ "$STASHED" == true ]]; then
  if git stash pop; then
    echo "[OK]   Stash restored cleanly."
  else
    echo "[WARN] Stash conflict — stash left in place. Run: git stash list"
  fi
fi

# 5. Reinstall deps if manifests changed
if git diff HEAD@{1} --name-only 2>/dev/null | grep -q 'package.*json'; then
  echo "[INFO] package.json changed — running npm ci…"
  npm ci --prefer-offline --silent && echo "[OK] npm ci done."
fi

if git diff HEAD@{1} --name-only 2>/dev/null | grep -q 'requirements'; then
  echo "[INFO] requirements.txt changed — pip install…"
  python3 -m pip install -q -r requirements.txt && echo "[OK] pip done."
fi

echo "[DONE] Auto-update complete."
UPDATER

  chmod +x "$UPDATER_SCRIPT"
  _ok "Auto-update script written to ${UPDATER_SCRIPT}"

  # ── Register with cron ────────────────────────────────────────────────────
  if command -v crontab &>/dev/null; then
    CRON_JOB="${UPDATE_CRON_SCHEDULE} ${UPDATER_SCRIPT}"
    if crontab -l 2>/dev/null | grep -qF "$UPDATER_SCRIPT"; then
      _skip "Cron job already registered"
    else
      ( crontab -l 2>/dev/null; echo "$CRON_JOB" ) | crontab -
      _ok "Cron job registered: ${UPDATE_CRON_SCHEDULE}"
    fi
  fi

  # ── Register with launchd on macOS ────────────────────────────────────────
  if [[ "$(uname -s)" == "Darwin" ]]; then
    PLIST="$HOME/Library/LaunchAgents/com.${REPO_NAME}.autoupdate.plist"
    if [[ ! -f "$PLIST" ]]; then
      cat > "$PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>         <string>com.${REPO_NAME}.autoupdate</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${UPDATER_SCRIPT}</string>
  </array>
  <key>StartInterval</key> <integer>21600</integer>
  <key>RunAtLoad</key>     <false/>
  <key>StandardOutPath</key>  <string>${INSTALL_DIR}/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>${INSTALL_DIR}/logs/launchd.err</string>
</dict>
</plist>
PLIST
      launchctl load "$PLIST" >>"$LOG_FILE" 2>&1 \
        && _ok "launchd agent registered" \
        || _warn "launchctl load failed — run: launchctl load ${PLIST}"
    else
      _skip "launchd plist already exists"
    fi
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 7 — WRITE SHELL ALIASES & COMPLETIONS
# ══════════════════════════════════════════════════════════════════════════════
write_aliases() {
  _step "Write shell aliases and completions"

  ALIAS_FILE="${CONFIG_DIR}/aliases.sh"
  cat > "$ALIAS_FILE" << ALIASES
# hacker-tool — Shell aliases
# Source this from your .bashrc / .zshrc:
#   source "${CONFIG_DIR}/aliases.sh"

alias ht='python3 ${INSTALL_DIR}/ht_launcher.py'
alias ht-update='${INSTALL_DIR}/scripts/auto-update.sh'
alias ht-log='tail -f ${INSTALL_DIR}/logs/auto-update-\$(date +%Y%m%d).log'
alias ht-config='${EDITOR:-nano} ${CONFIG_DIR}/config.toml'
alias ht-status='cd ${INSTALL_DIR} && git status && git log --oneline -5'
ALIASES

  _ok "Aliases written to ${ALIAS_FILE}"

  SOURCE_LINE="source \"${ALIAS_FILE}\""
  if [[ -n "${SHELL_RC:-}" ]] && ! grep -qF "$ALIAS_FILE" "${SHELL_RC}" 2>/dev/null; then
    printf '\n# hacker-tool aliases\n%s\n' "$SOURCE_LINE" >> "${SHELL_RC}"
    _ok "Alias source line added to ${SHELL_RC}"
  else
    _skip "Alias source already present in ${SHELL_RC:-shell RC}"
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 8 — FINAL HEALTH CHECKS
# ══════════════════════════════════════════════════════════════════════════════
health_checks() {
  _step "Final health checks"

  cd "$INSTALL_DIR"
  local HC_PASS=0 HC_WARN=0 HC_FAIL=0

  _check_pass() { _ok "$1";   (( HC_PASS++ )) || true; }
  _check_warn() { _warn "$1"; (( HC_WARN++ )) || true; }
  _check_fail() { _fail "$1"; (( HC_FAIL++ )) || true; }

  if git rev-parse --is-shallow-repository 2>/dev/null | grep -q 'true'; then
    _check_pass "Git repo integrity OK (shallow clone — fsck skipped)"
  else
    git fsck --no-dangling --quiet >>"$LOG_FILE" 2>&1 \
      && _check_pass "Git repo integrity OK" \
      || _check_warn "git fsck warnings — check ${LOG_FILE}"
  fi

  REMOTE="$(git remote get-url origin 2>/dev/null || echo '')"
  [[ -n "$REMOTE" ]] \
    && _check_pass "Remote 'origin' = ${REMOTE}" \
    || _check_fail "Remote 'origin' is not set"

  if [[ -f package.json ]]; then
    [[ -d node_modules ]] \
      && _check_pass "node_modules present" \
      || _check_fail "node_modules missing"
  fi

  if [[ -f requirements.txt ]]; then
    [[ -d .venv ]] || [[ -n "${VIRTUAL_ENV:-}" ]] \
      && _check_pass "Python venv present" \
      || _check_warn "Python venv not detected — deps may be global"
  fi

  BROKEN=0
  for link in "${BIN_DIR}/"*; do
    [[ -L "$link" ]] && [[ ! -e "$link" ]] && (( BROKEN++ )) || true
  done
  (( BROKEN == 0 )) \
    && _check_pass "No broken symlinks in ${BIN_DIR}" \
    || _check_warn "${BROKEN} broken symlink(s) in ${BIN_DIR}"

  [[ -x "${INSTALL_DIR}/scripts/auto-update.sh" ]] \
    && _check_pass "Auto-updater is executable" \
    || _check_fail "Auto-updater missing or not executable"

  [[ -f "${CONFIG_DIR}/config.toml" ]] \
    && _check_pass "Config file present: ${CONFIG_DIR}/config.toml" \
    || _check_fail "Config file missing"

  if command -v crontab &>/dev/null; then
    crontab -l 2>/dev/null | grep -qF "auto-update.sh" \
      && _check_pass "Cron auto-update registered" \
      || _check_warn "Cron auto-update not found in crontab"
  fi

  printf "\n"
  _ruler
  printf "  Health Check Results:  ${GREEN}%d passed${RESET}  /  ${YELLOW}%d warned${RESET}  /  ${RED}%d failed${RESET}\n" \
    "$HC_PASS" "$HC_WARN" "$HC_FAIL"
  _ruler

  return "$HC_FAIL"
}

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 9 — FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
final_report() {
  _step "Bootstrap complete — final report"

  printf "\n"

  if (( ${#ERRORS[@]} == 0 )); then
    printf "${BOLD}${GREEN}"
    cat << 'SUCCESS'
   ／l、
（ﾟ､ ｡ ７    Bootstrap completed successfully!
  l  ~ヽ
  じしf_,)ノ
SUCCESS
    printf "${RESET}"
  else
    printf "${BOLD}${YELLOW}  Bootstrap finished with %d error(s):\n${RESET}" "${#ERRORS[@]}"
    for e in "${ERRORS[@]}"; do printf "  ${RED}✘${RESET}  %s\n" "$e"; done
  fi

  if (( ${#WARNINGS[@]} > 0 )); then
    printf "\n  ${YELLOW}Warnings (${#WARNINGS[@]}):\n${RESET}"
    for w in "${WARNINGS[@]}"; do printf "  ${YELLOW}⚠${RESET}  %s\n" "$w"; done
  fi

  if (( ${#SKIPPED[@]} > 0 )); then
    printf "\n  ${MAGENTA}Skipped (${#SKIPPED[@]}):\n${RESET}"
    for s in "${SKIPPED[@]}"; do printf "  ${MAGENTA}↷${RESET}  %s\n" "$s"; done
  fi

  _ruler
  printf "  ${DIM}Full log saved to: ${LOG_FILE}${RESET}\n"
  _ruler

  printf "\n${BOLD}  Next steps:${RESET}\n"
  printf "  1.  Reload your shell:   ${CYAN}source ${SHELL_RC:-~/.bashrc}${RESET}\n"
  printf "  2.  Verify the tool:     ${CYAN}ht --version${RESET}\n"
  printf "  3.  Edit config:         ${CYAN}ht-config${RESET}\n"
  printf "  4.  Manual update:       ${CYAN}ht-update${RESET}\n"
  printf "  5.  Watch update log:    ${CYAN}ht-log${RESET}\n"
  printf "\n"
}

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
main() {
  mkdir -p "$(dirname "$LOG_FILE")"
  printf "hacker-tool bootstrap log — %s\n%s\n\n" \
    "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    "$(printf '%.0s─' {1..60})" > "$LOG_FILE"

  _banner

  if [[ "$K1LLLAGT" == "K1LLLAGT" ]]; then
    read -r -p "$(printf "  ${YELLOW}Enter your GitHub username:${RESET} ")" INPUT_USER
    K1LLLAGT="${INPUT_USER:-K1LLLAGT}"
    GITHUB_REMOTE="git@github.com:${K1LLLAGT}/${REPO_NAME}.git"
    GITHUB_HTTPS="https://github.com/${K1LLLAGT}/${REPO_NAME}.git"
    _info "Using GitHub username: ${K1LLLAGT}"
  fi

  preflight
  clone_or_update
  install_deps
  link_globals
  configure_remote
  create_config
  install_autoupdate
  write_aliases
  health_checks || HEALTH_FAILED=$?
  final_report

  exit "${HEALTH_FAILED:-0}"
}

main "$@"
