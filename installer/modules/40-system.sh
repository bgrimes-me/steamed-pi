# shellcheck shell=bash
# Step "system": the root-level setup: permissions, console session, login, firewall, network, lean-down.
# Everything here is reversible by ./uninstall.sh and backs up any file it edits (as FILE.before-steamed-pi).

# services that are pure overhead on a game console, in both modes
OVERHEAD_SERVICES=(NetworkManager-wait-online.service apport.service apport-autoreport.path apport-autoreport.timer apport-forward.socket
  kdump-tools.service rsyslog.service openvpn.service anacron.service anacron.timer
  sssd.service sssd-autofs.socket sssd-nss.socket sssd-pac.socket sssd-pam.socket sssd-ssh.socket sssd-sudo.socket)
# services that only Desktop mode needs: they start with GNOME and stop when you switch to Gaming Mode
DESKTOP_ONLY_SERVICES=(snapd cups cups-browsed ModemManager power-profiles-daemon switcheroo-control unattended-upgrades colord ubuntu-advantage-desktop-daemon)

_unit_exists() { systemctl list-unit-files "$1" --no-legend 2>/dev/null | grep -q "^$1"; }

mod_system() {
  step "Setting up the console session and system settings"
  local s="$REPO_DIR"

  # 1. sudo rules (validated before they are installed: a broken sudoers file would lock you out of sudo)
  local tmp; tmp=$(mktemp); sed "s|@USER@|$TARGET_USER|g" "$s/system/sudoers.in" > "$tmp"
  if [ "$DRY" = 1 ] || visudo -cf "$tmp" >/dev/null 2>&1; then as_root install -m 0440 -o root -g root "$tmp" /etc/sudoers.d/steamed-pi && ok "sudo rules installed (a short list of specific commands, no password)"
  else rm -f "$tmp"; die "the sudo rules failed validation: not installing them"; fi
  rm -f "$tmp"

  # 2. the "Console Mode" login session (a minimal compositor running Steam Big Picture)
  render_root "$s/src/desktop/steamed-pi-console.desktop.in" /usr/share/wayland-sessions/steamed-pi-console.desktop 644 && ok "Console Mode session registered"

  # 3. desktop-only services follow steamed-pi-desktop.target
  as_root install -m 644 "$s/system/steamed-pi-desktop.target" /etc/systemd/system/steamed-pi-desktop.target
  local u
  for u in "${DESKTOP_ONLY_SERVICES[@]}"; do
    _unit_exists "$u.service" || continue
    as_root mkdir -p "/etc/systemd/system/$u.service.d"
    printf '[Unit]\n# Steamed Pi: stop with the desktop-only target (Gaming Mode)\nPartOf=steamed-pi-desktop.target\n' | as_root tee "/etc/systemd/system/$u.service.d/steamed-pi.conf" >/dev/null
    as_root systemctl disable "$u.service" >/dev/null 2>&1 || true
  done
  for u in "${OVERHEAD_SERVICES[@]}"; do _unit_exists "$u" && as_root systemctl disable --now "$u" >/dev/null 2>&1; done
  as_root systemctl daemon-reload; ok "background services trimmed (desktop-only ones now start only in Desktop mode)"

  # 4. log in automatically, straight to the chosen mode
  local c=/etc/gdm3/custom.conf
  if [ -f "$c" ]; then
    backup_once "$c"
    as_root python3 -I - "$c" "$TARGET_USER" <<'PY'
import re, sys
p, user = sys.argv[1], sys.argv[2]; s = open(p).read()
s = re.sub(r'^\s*#?\s*AutomaticLoginEnable\s*=.*\n', '', s, flags=re.M); s = re.sub(r'^\s*#?\s*AutomaticLogin\s*=.*\n', '', s, flags=re.M)
s = s.replace('[daemon]\n', '[daemon]\nAutomaticLoginEnable=true\nAutomaticLogin=%s\n' % user, 1); open(p, 'w').write(s)
PY
    ok "automatic login enabled for $TARGET_USER (your password still works for sudo and SSH)"
  else warn "$c not found; automatic login not configured"; fi

  # 5. let the dashboard's FTP server use the standard port 21
  echo 'net.ipv4.ip_unprivileged_port_start = 21' | as_root tee /etc/sysctl.d/60-steamed-pi-lowports.conf >/dev/null; as_root sysctl -q -p /etc/sysctl.d/60-steamed-pi-lowports.conf 2>/dev/null

  # 6. answer on the interface a request arrived on (so wired and Wi-Fi addresses both work, on any network)
  as_root install -m 0755 -o root -g root "$s/system/90-steamed-pi-policy-routing" /etc/NetworkManager/dispatcher.d/90-steamed-pi-policy-routing && ok "network hook installed"

  # 7. firewall: nothing in from the internet; the dashboard, SSH, FTP and Steam streaming only from private (home) networks
  if command -v ufw >/dev/null 2>&1; then
    as_root ufw default deny incoming >/dev/null; as_root ufw default allow outgoing >/dev/null
    local net
    for net in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
      as_root ufw allow from "$net" to any port 8080 proto tcp comment 'steamed-pi dashboard' >/dev/null
      as_root ufw allow from "$net" to any port 22 proto tcp comment 'steamed-pi ssh' >/dev/null
      as_root ufw allow from "$net" to any port 21 proto tcp comment 'steamed-pi ftp' >/dev/null
      as_root ufw allow from "$net" to any port 30000:30009 proto tcp comment 'steamed-pi ftp data' >/dev/null
      as_root ufw allow from "$net" to any port 5353 proto udp comment 'steamed-pi mdns' >/dev/null
      as_root ufw allow from "$net" to any port 27031:27036 proto udp comment 'steam streaming' >/dev/null
      as_root ufw allow from "$net" to any port 10400:10401 proto udp comment 'steam streaming' >/dev/null
      as_root ufw allow from "$net" to any port 27036:27037 proto tcp comment 'steam streaming' >/dev/null
      as_root ufw allow from "$net" to any port 27040 proto tcp comment 'steam lan transfer' >/dev/null
    done
    as_root ufw --force enable >/dev/null && as_root systemctl enable ufw >/dev/null 2>&1; ok "firewall on (private networks only)"
  fi

  # 8. the network name: "steamed-pi" by default on the first install (change it any time: Settings page, dashboard, or
  #    `steamed-pi-setting set hostname NAME`). A name you have chosen is never overwritten by a later install.
  as_root install -m 0755 -o root -g root "$s/system/steamed-pi-set-hostname" /usr/local/sbin/steamed-pi-set-hostname
  local want=${HOSTNAME_ARG:-steamed-pi} marker="$CFG_DIR/steamed-pi/hostname-chosen" cur; cur=$(hostname)
  if [ -f "$marker" ]; then info "network name: keeping '$cur' (chosen earlier)"
  elif [ "$want" = keep ]; then as_user mkdir -p "$(dirname "$marker")"; as_user touch "$marker"; info "network name: keeping '$cur'"
  elif [ "$cur" = "$want" ]; then as_user mkdir -p "$(dirname "$marker")"; as_user touch "$marker"; ok "network name is already $want"
  else
    local n; n=$("$s/system/steamed-pi-set-hostname" --check "$want") || { warn "'$want' is not a valid network name; keeping '$cur'"; n=""; }
    if [ -n "$n" ] && as_root /usr/local/sbin/steamed-pi-set-hostname "$n" >/dev/null; then as_user mkdir -p "$(dirname "$marker")"; as_user touch "$marker"; ok "network name set to $n  (reach it at $n.local)"; fi
  fi

  # 9. the dashboard must run at boot without anyone logged in
  as_root loginctl enable-linger "$TARGET_USER" && ok "dashboard will start at boot"
  return 0
}
