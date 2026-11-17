# shellcheck shell=bash
# Step "packages": everything Steamed Pi needs from Ubuntu's own repositories.
mod_packages() {
  step "Installing packages"
  local core=(
    labwc wlr-randr libgtk4-layer-shell0 gir1.2-gtk4layershell-1.0     # the console-mode compositor and menu overlay
    python3-gi gir1.2-gtk-4.0 x11-utils                                # menu overlay + window tools
    openssh-server python3-pyftpdlib ufw                               # remote access (off until you switch it on) and firewall
    libopenal1 libgtk2.0-0t64 libsdl3-0                                # libraries Valve's Steam client loads
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good   # builds the startup movie from a still image
    plymouth plymouth-label curl ca-certificates unzip
  )
  # FFmpeg and dav1d libraries carry a version number in their package name that changes between Ubuntu releases: look it up
  local lib name
  for lib in '^libavcodec[0-9]+$' '^libavformat[0-9]+$' '^libavutil[0-9]+$' '^libswscale[0-9]+$' '^libswresample[0-9]+$' '^libdav1d[0-9]+$'; do
    apt_update_once; name=$(newest_pkg "$lib"); [ -n "$name" ] && core+=("$name") || warn "no package matches $lib (Steam's media playback may be limited)"
  done
  apt_install "${core[@]}" || return 1
  # Valve's client asks for libdav1d.so.6 by name; Ubuntu ships a newer soname. Provide the old name pointing at the current library.
  local dav; dav=$(ls /usr/lib/aarch64-linux-gnu/libdav1d.so.[0-9]* 2>/dev/null | sort -V | tail -1)
  if [ -n "$dav" ] && [ ! -e /usr/local/lib/libdav1d.so.6 ] && [ "$(basename "$dav")" != libdav1d.so.6 ]; then
    as_root install -D -m 644 "$dav" /usr/local/lib/libdav1d.so.6 && as_root ldconfig && ok "libdav1d.so.6 provided from $(basename "$dav")"
  fi
  # SSH stays OFF until the dashboard or Settings page turns it on
  as_root systemctl disable --now ssh.socket ssh.service >/dev/null 2>&1 || true
  ok "packages done"
}
