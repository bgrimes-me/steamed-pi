# shellcheck shell=bash
# Step "preflight": make sure this is a machine Steamed Pi can work on, before changing anything.
mod_preflight() {
  step "Checking this machine"
  local bad=0 model
  [ "$(uname -m)" = aarch64 ] || { warn "This is $(uname -m); Steamed Pi needs a 64-bit ARM (aarch64) system."; bad=1; }
  model=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
  case $model in
    *"Raspberry Pi 5"*) ok "Raspberry Pi 5 detected";;
    *Raspberry*) warn "Found '$model'. Steamed Pi is built and tested on the Pi 5; the Steam ARM client and GPU driver work differs on other models."; [ "$FORCE" = 1 ] || bad=1;;
    *) warn "Could not identify a Raspberry Pi ('${model:-unknown}')."; [ "$FORCE" = 1 ] || bad=1;;
  esac
  . /etc/os-release 2>/dev/null
  if [ "${ID:-}" = ubuntu ]; then ok "Ubuntu ${VERSION_ID:-?}"; [ "${VERSION_ID:-}" = 26.10 ] || warn "Steamed Pi was built and tested on Ubuntu 26.10; this is ${VERSION_ID:-unknown}. It will probably work, but please report problems."; else warn "Not Ubuntu (${PRETTY_NAME:-unknown}). Steamed Pi is built for Ubuntu Desktop on the Pi."; [ "$FORCE" = 1 ] || bad=1; fi
  if [ -f /usr/share/wayland-sessions/ubuntu.desktop ] && { pkg_installed gdm3 || [ "$DRY" = 1 ]; }; then ok "GNOME desktop with GDM found"
  else warn "GNOME/GDM was not found. Install Ubuntu *Desktop* for the Raspberry Pi (not Server)."; bad=1; fi
  local ps; ps=$(getconf PAGESIZE)
  if [ "$ps" = 4096 ]; then ok "4 KB memory pages (needed by Valve's Steam client)"
  else warn "This kernel uses ${ps}-byte memory pages. Valve's ARM Steam client needs 4096. Boot a 4K-page kernel (on Ubuntu for Pi 5 that is the default 'raspi' kernel; Raspberry Pi OS's kernel8 default is 16K) and run the installer again."; bad=1; fi
  local free; free=$(df -Pk "$TARGET_HOME" | awk 'NR==2{print int($4/1048576)}')
  if [ "${free:-0}" -ge 8 ]; then ok "${free} GB free"; else warn "Only ${free:-?} GB free in $TARGET_HOME; need at least 8 GB (more for games)."; bad=1; fi
  if curl -sfI -m 20 https://client-update.steamstatic.com/steam_client_linuxarm64 >/dev/null 2>&1; then ok "can reach Valve's download server"
  else warn "Cannot reach client-update.steamstatic.com. Check the network connection."; bad=1; fi
  if [ "$DRY" != 1 ] && ! sudo -n true 2>/dev/null && [ "$(id -u)" != 0 ]; then warn "sudo does not work for $TARGET_USER."; bad=1; fi
  if [ $bad = 1 ]; then
    [ "$DRY" = 1 ] && { warn "(dry run: continuing anyway)"; return 0; }
    return 1
  fi
  return 0
}
