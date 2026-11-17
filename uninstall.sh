#!/bin/bash
# Remove Steamed Pi's system changes and files. Your games, ROMs, saves and Steam login are NOT touched.
#   ./uninstall.sh            remove everything Steamed Pi added (keeps Steam, ES-DE, RetroArch and your ROMs)
#   ./uninstall.sh --purge    also remove Steam, ES-DE and RetroArch (never ~/ROMs and never Steam game files)
set -uo pipefail
HERE=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd); export REPO_DIR=$HERE
PURGE=0; for a in "$@"; do case $a in --purge) PURGE=1;; --dry-run) export DRY=1;; --yes|-y) export ASSUME_YES=1;; *) echo "unknown option $a"; exit 2;; esac; done
. "$HERE/installer/lib.sh"
[ "$TARGET_USER" = root ] && die "Run as your normal user."
. "$HERE/installer/modules/40-system.sh"      # for the service lists
step "Removing Steamed Pi for $TARGET_USER"
confirm "This switches the console off and restores the stock desktop settings. Continue?" || exit 0

# 1. go back to the normal Ubuntu session, and undo the desktop look
as_user "$BIN_DIR/steamed-pi-session-switch" boot desktop >/dev/null 2>&1
have_user_bus && as_user_session bash "$SP_DIR/theme/steamed-pi-theme.sh" undo >/dev/null 2>&1
as_user_session systemctl --user disable --now steamed-pi-dashboard.service steamed-pi-controller-home.service >/dev/null 2>&1

# 2. system changes
as_root rm -f /usr/local/sbin/steamed-pi-set-hostname /etc/cloud/cloud.cfg.d/99-steamed-pi-hostname.cfg /etc/sudoers.d/steamed-pi /usr/share/wayland-sessions/steamed-pi-console.desktop /etc/sysctl.d/60-steamed-pi-lowports.conf /etc/NetworkManager/dispatcher.d/90-steamed-pi-policy-routing
as_root systemctl stop steamed-pi-desktop.target >/dev/null 2>&1
for u in "${DESKTOP_ONLY_SERVICES[@]}"; do as_root rm -f "/etc/systemd/system/$u.service.d/steamed-pi.conf"; as_root rmdir "/etc/systemd/system/$u.service.d" 2>/dev/null; as_root systemctl enable "$u.service" >/dev/null 2>&1; done
for u in "${OVERHEAD_SERVICES[@]}"; do :; done      # these were disabled for speed; left disabled (re-enable with systemctl enable if you need one)
as_root rm -f /etc/systemd/system/steamed-pi-desktop.target; as_root systemctl daemon-reload
for f in /etc/gdm3/custom.conf /etc/gdm3/greeter.dconf-defaults; do [ -f "$f.before-steamed-pi" ] && as_root mv -f "$f.before-steamed-pi" "$f"; done
as_root update-alternatives --remove gdm-theme.gresource /usr/local/share/steamed-pi/gdm-theme.gresource >/dev/null 2>&1; as_root rm -rf /usr/local/share/steamed-pi
as_root loginctl disable-linger "$TARGET_USER"
# the boot splash goes back to Ubuntu's default
if [ -f /usr/share/plymouth/themes/btgprojects/btgprojects.plymouth ]; then
  as_root update-alternatives --remove default.plymouth /usr/share/plymouth/themes/btgprojects/btgprojects.plymouth >/dev/null 2>&1
  as_root rm -rf /usr/share/plymouth/themes/btgprojects; as_root update-initramfs -u -k "$(uname -r)" >/dev/null 2>&1
fi
# firewall rules we added
if command -v ufw >/dev/null 2>&1; then
  while read -r n; do as_root ufw --force delete "$n" >/dev/null 2>&1; done < <(ufw status numbered 2>/dev/null | grep -E 'steamed-pi|steam streaming|steam lan' | sed -E 's/^\[ *([0-9]+)\].*/\1/' | sort -rn)
fi

# 3. user files
as_user rm -rf "$SP_DIR" "$ART_DIR" "$CFG_DIR/steamed-pi/labwc" "$CFG_DIR/steamed-pi" "$TARGET_HOME/.local/state/steamed-pi"
for f in steamed-pi-controller-home.py es-de-launch retroarch dolphin-emu steamed-pi-console-session steamed-pi-console-start steamed-pi-inventory steamed-pi-overlay steamed-pi-restart-steam steamed-pi-session-switch steamed-pi-setting steamed-pi-steam-supervisor steamed-pi-window-log steamed-pi-bench steamed-pi-postlogin steamed-pi-first-login; do as_user rm -f "$BIN_DIR/$f"; done
as_user rm -rf "$LIB_DIR"
as_user rm -f "$TARGET_HOME"/.local/share/icons/hicolor/*/apps/steamed-pi-gaming-mode.*
for f in steamed-pi-controller-home steamed-pi-boot-default steamed-pi-dashboard steamed-pi-desktop-mode steamed-pi-overlay-attention steamed-pi-session-refresh; do as_user rm -f "$CFG_DIR/systemd/user/$f.service" "$CFG_DIR"/systemd/user/*.wants/"$f.service"; done
as_user rm -f "$TARGET_HOME/.local/share/applications/steamed-pi-gaming-mode.desktop" "$TARGET_HOME/.local/share/applications/steam-native.desktop" "$CFG_DIR/autostart/steamed-pi-first-login.desktop"
if [ "$PURGE" = 1 ]; then
  as_user rm -rf "$STEAM_DIR" "$TARGET_HOME/.steam" "$TARGET_HOME/Applications/ES-DE" "$TARGET_HOME/Applications/RetroArch-nightly"
  info "Steam client, ES-DE and RetroArch removed. Your ROMs (~/ROMs) and Steam games were left alone."
fi
step "Done"; info "Reboot to finish. Your console name ($(hostname)) was left as it is, and the installed packages (labwc, ufw, ...) stay; remove them with apt if you want."
