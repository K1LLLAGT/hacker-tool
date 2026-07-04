#!/usr/bin/env bash
#
# ht-bootstrap.sh — full Hacker-Tool bootstrap for Termux/Ubuntu
# Deterministic, CAT-style: deps → repo → remote → gh → htctl → launcher.
#
set -euo pipefail

### CONFIG #####################################################################

# GitHub owner + repo
HT_GH_OWNER="K1LLLAGT"
HT_GH_REPO="hacker-tool"

# Local project root
HT_ROOT="${HOME}/hacker-tool"

# Remote URL (SSH)
HT_REMOTE="git@github.com:${HT_GH_OWNER}/${HT_GH_REPO}.git"

# Termux prefix (auto-detected if not set)
TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"

# Paths for global commands
BIN_DIR="${TERMUX_PREFIX}/bin"
HTCTL_GLOBAL="${BIN_DIR}/htctl"
HT_LAUNCHER_GLOBAL="${BIN_DIR}/ht"
HT_CLI_GLOBAL="${BIN_DIR}/hackertool"

###############################################################################
# Helpers
###############################################################################

log() { printf '\n[ht-bootstrap] %s\n' "$*" >&2; }
die() { printf '\n[ht-bootstrap:ERROR] %s\n' "$*" >&2; exit 1; }

is_termux() {
  [[ -d "/data/data/com.termux/files/usr" ]] && return 0 || return 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

###############################################################################
# Step 1: Environment + deps
###############################################################################

step_env() {
  log "Step 1: Detect environment and install core deps"

  if is_termux; then
    log "Detected Termux environment"
    PKG="pkg"
  elif have_cmd "apt"; then
    log "Detected generic Debian/Ubuntu environment"
    PKG="sudo apt-get"
  else
    die "Unsupported environment: need Termux or apt-based Linux"
  fi

  # Core tools
  CORE_PKGS=(python git nmap iproute2 samba)

  log "Installing core packages: ${CORE_PKGS[*]}"
  if [[ "${PKG}" == "pkg" ]]; then
    pkg update -y
    pkg install -y "${CORE_PKGS[@]}"
  else
    ${PKG} update -y
    ${PKG} install -y "${CORE_PKGS[@]}"
  fi

  log "Core deps installed"
}

###############################################################################
# Step 2: Repo setup (clone or init)
###############################################################################

step_repo() {
  log "Step 2: Ensure ${HT_ROOT} exists and is a git repo"

  if [[ -d "${HT_ROOT}/.git" ]]; then
    log "Existing git repo found at ${HT_ROOT}"
    return 0
  fi

  if [[ -d "${HT_ROOT}" ]]; then
    log "Directory ${HT_ROOT} exists but is not a git repo — initializing"
    cd "${HT_ROOT}"
    git init
  else
    log "Directory ${HT_ROOT} does not exist — creating and initializing"
    mkdir -p "${HT_ROOT}"
    cd "${HT_ROOT}"
    git init
  fi

  # Basic initial commit if empty
  if [[ -z "$(git status --porcelain)" ]]; then
    log "No files tracked yet — you should copy your hacker-tool tree here before committing."
    log "For now, leaving repo empty. You can rerun bootstrap after adding files."
  else
    log "Repo has files — ensuring main branch"
    git branch -M main
  fi
}

###############################################################################
# Step 3: Remote + GitHub repo via gh
###############################################################################

step_remote_and_gh() {
  log "Step 3: Configure remote and GitHub repo"

  cd "${HT_ROOT}"

  if ! have_cmd "gh"; then
    die "GitHub CLI (gh) not found. Install it before running this step."
  fi

  # Set remote if missing
  if ! git remote get-url origin >/dev/null 2>&1; then
    log "Adding origin remote: ${HT_REMOTE}"
    git remote add origin "${HT_REMOTE}"
  else
    log "Origin remote already set: $(git remote get-url origin)"
  fi

  # Try to create repo if it doesn't exist
  log "Ensuring GitHub repo ${HT_GH_OWNER}/${HT_GH_REPO} exists"
  if ! gh repo view "${HT_GH_OWNER}/${HT_GH_REPO}" >/dev/null 2>&1; then
    log "Creating GitHub repo via gh"
    gh repo create "${HT_GH_REPO}" \
      --public \
      --source=. \
      --push \
      --remote=origin || log "Repo create remote step may have failed; continuing"
  else
    log "GitHub repo already exists; pushing local main"
    git push -u origin main || log "Push failed; check SSH/auth manually"
  fi
}

###############################################################################
# Step 4: Drop in htctl + launcher if missing
###############################################################################

step_files() {
  log "Step 4: Ensure htctl and ht_launcher.py exist"

  cd "${HT_ROOT}"

  # These assume you already have the canonical versions in your repo.
  # If not, you can paste them in once and this step will just verify.

  if [[ ! -f "htctl" ]]; then
    die "htctl not found in ${HT_ROOT}. Add your htctl script to the repo first."
  fi

  if [[ ! -f "ht_launcher.py" ]]; then
    die "ht_launcher.py not found in ${HT_ROOT}. Add your launcher to the repo first."
  fi

  chmod +x htctl
  log "htctl present and executable"
}

###############################################################################
# Step 5: Link global commands into Termux/Ubuntu
###############################################################################

step_link() {
  log "Step 5: Link htctl, ht, hackertool into ${BIN_DIR}"

  mkdir -p "${BIN_DIR}"

  cd "${HT_ROOT}"

  # htctl
  ln -sf "${HT_ROOT}/htctl" "${HTCTL_GLOBAL}"
  log "Linked htctl -> ${HTCTL_GLOBAL}"

  # ht (launcher)
  cat > "${HT_LAUNCHER_GLOBAL}" <<EOF
#!/usr/bin/env bash
exec python "${HT_ROOT}/ht_launcher.py" "\$@"
EOF
  chmod +x "${HT_LAUNCHER_GLOBAL}"
  log "Linked ht (launcher) -> ${HT_LAUNCHER_GLOBAL}"

  # hackertool (CLI)
  cat > "${HT_CLI_GLOBAL}" <<EOF
#!/usr/bin/env bash
exec python "${HT_ROOT}/hacker-tool.py" "\$@"
EOF
  chmod +x "${HT_CLI_GLOBAL}"
  log "Linked hackertool (CLI) -> ${HT_CLI_GLOBAL}"
}

###############################################################################
# Step 6: htctl doctor + deps
###############################################################################

step_htctl() {
  log "Step 6: Run htctl doctor + deps"

  cd "${HT_ROOT}"

  # Ensure HT_REMOTE is visible to htctl
  export HT_REMOTE="${HT_REMOTE}"

  ./htctl deps || log "htctl deps reported issues; check output"
  ./htctl doctor || log "htctl doctor reported issues; check output"
}

###############################################################################
# Step 7: Smoke test launcher
###############################################################################

step_smoke() {
  log "Step 7: Smoke test launcher (dry-run)"

  cd "${HT_ROOT}"

  # Dry-run via settings flag (if you have one) or just rely on TOOL
  log "Running ht launcher in dry-run mode; use Network → Ping sweep with 10.0.0.0/24"
  python ht_launcher.py <<EOF || true
q
EOF

  log "Bootstrap complete. You should now have:"
  log "  - htctl, ht, hackertool in PATH"
  log "  - Git repo at ${HT_ROOT}"
  log "  - Remote ${HT_REMOTE}"
  log "  - GitHub repo ${HT_GH_OWNER}/${HT_GH_REPO} (if gh was configured)"
}

###############################################################################
# Main
###############################################################################

main() {
  log "Starting full Hacker-Tool bootstrap"

  step_env
  step_repo
  step_remote_and_gh
  step_files
  step_link
  step_htctl
  step_smoke

  log "All steps finished."
}

main "$@"

chmod +x ht-bootstrap.sh
