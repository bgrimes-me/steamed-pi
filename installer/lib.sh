# shellcheck shell=bash
# Shared helpers for the Steamed Pi installer. Sourced by install.sh / uninstall.sh; do not run directly.

# ---- who and where (everything below derives from these; nothing is hardcoded to a person or machine)
if [ -n "${STEAMED_PI_USER:-}" ]; then TARGET_USER=$STEAMED_PI_USER
elif [ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ]; then TARGET_USER=$SUDO_USER
else TARGET_USER=$(id -un); fi
TARGET_HOME=${STEAMED_PI_HOME:-$(getent passwd "$TARGET_USER" | cut -d: -f6)}      # STEAMED_PI_HOME: for testing into a scratch folder
TARGET_UID=$(id -u "$TARGET_USER" 2>/dev/null || echo 1000)
SP_DIR="$TARGET_HOME/.local/share/steamed-pi"          # the app: dashboard, theme, plymouth, tools
BIN_DIR="$TARGET_HOME/.local/bin"                        # the commands
LIB_DIR="$TARGET_HOME/.local/lib/steamed-pi"                  # the python libraries
ART_DIR="$TARGET_HOME/.local/share/steamed-pi/art"        # brand art + startup movie (swap these to re-brand)
STEAM_DIR="$TARGET_HOME/.local/share/Steam"
CFG_DIR="$TARGET_HOME/.config"
REPO_DIR=${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
DRY=${DRY:-0}; ASSUME_YES=${ASSUME_YES:-0}; FORCE=${FORCE:-0}
LOG_FILE=${LOG_FILE:-$TARGET_HOME/.cache/steamed-pi-install.log}

# ---- scratch mode: STEAMED_PI_HOME points the whole install at a throwaway folder (used by the tests).
# In scratch mode nothing may touch the real machine: no sudo/root steps, no login-session changes, no user-service changes.
SCRATCH=0; [ -n "${STEAMED_PI_HOME:-}" ] && { SCRATCH=1; export STEAMED_PI_NO_ACCOUNT=1; }

# ---- output
if [ -t 1 ]; then C_B=$'\e[1m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_R=$'\e[31m'; C_0=$'\e[0m'; else C_B=; C_G=; C_Y=; C_R=; C_0=; fi
_log() { mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null && printf '%s %s\n' "$(date +%T)" "$*" >> "$LOG_FILE" 2>/dev/null || true; }
step()  { printf '\n%s==> %s%s\n' "$C_B" "$*" "$C_0"; _log "== $*"; }
info()  { printf '    %s\n' "$*"; _log "$*"; }
ok()    { printf '    %s✓%s %s\n' "$C_G" "$C_0" "$*"; _log "ok: $*"; }
warn()  { printf '    %s!%s %s\n' "$C_Y" "$C_0" "$*" >&2; _log "WARN: $*"; }
die()   { printf '\n%sERROR:%s %s\n' "$C_R" "$C_0" "$*" >&2; _log "ERROR: $*"; exit 1; }

# ---- running things (DRY=1 prints instead of doing)
run() { if [ "$DRY" = 1 ]; then printf '    [dry-run] %s\n' "$*"; return 0; fi; _log "\$ $*"; "$@"; }
as_root() {
  if [ "$SCRATCH" = 1 ]; then printf '    [scratch mode] skipped (needs root): %s\n' "$*"; return 0; fi
  if [ "$DRY" = 1 ]; then printf '    [dry-run] (as root) %s\n' "$*"; return 0; fi
  _log "# $*"; if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi
}
as_user() {
  if [ "$DRY" = 1 ]; then printf '    [dry-run] (as %s) %s\n' "$TARGET_USER" "$*"; return 0; fi
  _log "\$ $*"; if [ "$(id -un)" = "$TARGET_USER" ]; then "$@"; else sudo -u "$TARGET_USER" -H "$@"; fi
}
# user-session commands (systemctl --user, gsettings) need the user's runtime dir and bus
as_user_session() {
  local rt=/run/user/$TARGET_UID
  as_user env XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=$rt/bus" "$@"
}
have_user_bus() { [ "$SCRATCH" = 0 ] && [ -S "/run/user/$TARGET_UID/bus" ]; }
confirm() { [ "$ASSUME_YES" = 1 ] && return 0; local a; read -r -p "    $1 [y/N] " a; [[ $a =~ ^[Yy] ]]; }

# ---- files
render() {            # render SRC DST [mode] : fill in @HOME@ and @USER@, owned by the target user
  local src=$1 dst=$2 mode=${3:-644}
  if [ "$DRY" = 1 ]; then info "[dry-run] render $(basename "$src") -> $dst"; return 0; fi
  as_user mkdir -p "$(dirname "$dst")"
  sed -e "s|@HOME@|$TARGET_HOME|g" -e "s|@USER@|$TARGET_USER|g" "$src" | as_user tee "$dst" >/dev/null
  as_user chmod "$mode" "$dst"
}
copy_user() {         # copy_user SRC DST [mode]
  local src=$1 dst=$2 mode=${3:-}
  if [ "$DRY" = 1 ]; then info "[dry-run] copy $(basename "$src") -> $dst"; return 0; fi
  as_user mkdir -p "$(dirname "$dst")"; as_user cp -f "$src" "$dst"; [ -n "$mode" ] && as_user chmod "$mode" "$dst"; return 0
}
render_root() {       # render_root SRC DST [mode] : same, but a root-owned system file
  local src=$1 dst=$2 mode=${3:-644} tmp
  if [ "$DRY" = 1 ]; then info "[dry-run] render (root) $(basename "$src") -> $dst"; return 0; fi
  tmp=$(mktemp); sed -e "s|@HOME@|$TARGET_HOME|g" -e "s|@USER@|$TARGET_USER|g" "$src" > "$tmp"
  as_root install -D -m "$mode" -o root -g root "$tmp" "$dst"; rm -f "$tmp"
}
backup_once() { [ -f "$1" ] && [ ! -f "$1.before-steamed-pi" ] && as_root cp -p "$1" "$1.before-steamed-pi"; return 0; }

# ---- packages
APT_UPDATED=0
apt_update_once() { [ "$APT_UPDATED" = 1 ] && return 0; as_root apt-get update -qq && APT_UPDATED=1; }
pkg_installed() { dpkg -s "$1" >/dev/null 2>&1; }
pkg_available() { apt-cache show "$1" >/dev/null 2>&1; }
apt_install() {
  local want=() p
  for p in "$@"; do pkg_installed "$p" || want+=("$p"); done
  [ ${#want[@]} -eq 0 ] && { ok "already installed: $*"; return 0; }
  apt_update_once; info "installing: ${want[*]}"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "${want[@]}"
}
newest_pkg() {        # newest_pkg REGEX : newest available package whose name matches (e.g. '^libavcodec[0-9]+$')
  apt-cache pkgnames 2>/dev/null | grep -E "$1" | sort -V | tail -1
}
