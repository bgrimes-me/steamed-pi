#!/bin/bash
# Steamed Pi installer: turns a freshly installed Ubuntu Desktop on a Raspberry Pi 5 into a Steam-Deck-style game console.
#
#   ./install.sh                  install everything (you will be asked for your password once, for sudo)
#   ./install.sh --dry-run        show what would be done, change nothing
#   ./install.sh --no-emulation   skip ES-DE / RetroArch / Dolphin
#   ./install.sh --only steam,deploy      run only the named steps
#   ./install.sh --skip boot-look,emulation  run everything except these
#                                 steps, in order: preflight packages steam deploy system boot-look session emulation finish
#   ./install.sh --yes            do not ask questions
#   ./install.sh --hostname NAME  name the console NAME on the network (default: steamed-pi, only on the first install)
#   ./install.sh --keep-hostname  do not touch the machine's current name
#   ./install.sh --refresh-art    overwrite the installed artwork with the files in assets/ (after you rebrand them)
#   ./install.sh --force          re-download Steam even if present; continue past hardware warnings
#   ./install.sh --user NAME      install for the user NAME (when run by someone else, e.g. the first-boot service)
#
# Run it as your normal user (NOT with sudo). Safe to re-run: every step checks before it changes anything.
# Undo: ./uninstall.sh      Log: ~/.cache/steamed-pi-install.log
set -uo pipefail
HERE=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd); export REPO_DIR=$HERE

# argument parsing happens before lib.sh so --user can influence it
ONLY=""; SKIP=""; WITH_EMU=1
while [ $# -gt 0 ]; do case $1 in
  --dry-run) export DRY=1;; --yes|-y) export ASSUME_YES=1;; --force) export FORCE=1;;
  --no-emulation) WITH_EMU=0;; --hostname) export HOSTNAME_ARG=$2; shift;; --keep-hostname) export HOSTNAME_ARG=keep;; --refresh-art) export REFRESH_ART=1;; --only) ONLY=$2; shift;; --skip) SKIP=$2; shift;; --user) export STEAMED_PI_USER=$2; shift;;
  -h|--help) awk 'NR>1 && /^set -/{exit} NR>1{sub(/^# ?/,""); print}' "$0"; exit 0;;
  *) echo "unknown option: $1 (try --help)"; exit 2;; esac; shift; done

# shellcheck source=installer/lib.sh
. "$HERE/installer/lib.sh"
[ "$TARGET_USER" = root ] && die "Run this as your normal user, not root. (It uses sudo for the few steps that need it.)"
[ -d "$TARGET_HOME" ] || die "Home folder for '$TARGET_USER' not found."

STEPS=(preflight packages steam deploy system boot-look session emulation finish)
for m in "$HERE"/installer/modules/*.sh; do . "$m"; done

wanted() {   # wanted STEP
  local s=$1
  [ -n "$ONLY" ] && ! [[ ",$ONLY," == *",$s,"* ]] && return 1
  [[ ",$SKIP," == *",$s,"* ]] && return 1
  [ "$s" = emulation ] && [ "$WITH_EMU" = 0 ] && return 1
  return 0
}

printf '%sSteamed Pi installer%s  (user: %s, home: %s)%s\n' "$C_B" "$C_0" "$TARGET_USER" "$TARGET_HOME" "$([ "$DRY" = 1 ] && echo '  [DRY RUN]')"
# only ask for the sudo password if a step that needs root is going to run
NEED_ROOT=0; for s in packages system boot-look emulation; do wanted "$s" && NEED_ROOT=1; done
if [ "$DRY" != 1 ] && [ "$SCRATCH" = 0 ] && [ "$(id -u)" != 0 ] && [ "$NEED_ROOT" = 1 ]; then
  info "Asking for sudo once (needed to install packages and system settings)..."
  sudo -v || die "sudo is required."
  ( while true; do sudo -n true 2>/dev/null; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) &   # keep the sudo ticket alive
fi

FAILED=()
for s in "${STEPS[@]}"; do
  wanted "$s" || { info "skipping step: $s"; continue; }
  fn="mod_${s//-/_}"
  if ! "$fn"; then
    FAILED+=("$s"); warn "step '$s' did not complete."
    # a failed preflight or package step means the later ones cannot work: stop. Others are independent.
    case $s in preflight|packages) die "Cannot continue. Fix the problem above and run ./install.sh again.";; esac
  fi
done
if [ ${#FAILED[@]} -gt 0 ]; then
  printf '\n%sFinished with problems in: %s%s\nSee %s, fix the cause, and run ./install.sh again (it only redoes what is missing).\n' "$C_Y" "${FAILED[*]}" "$C_0" "$LOG_FILE"; exit 1
fi
