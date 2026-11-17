# shellcheck shell=bash
# Step "boot-look": the boot splash and the login screen, so even a brief flash of either is on brand.
mod_boot_look() {
  step "Boot splash and login screen"
  local rc=0
  _boot_splash || rc=1
  _login_theme || rc=1
  return $rc
}

_boot_splash() {
  local src="$SP_DIR/plymouth/btgprojects" dst=/usr/share/plymouth/themes/btgprojects kver; kver=$(uname -r)
  if [ "$DRY" != 1 ] && [ ! -f "$src/btgprojects.plymouth" ]; then warn "splash theme not deployed yet (run the 'deploy' step first)"; return 1; fi
  if ! command -v update-initramfs >/dev/null 2>&1; then warn "update-initramfs not found: skipping the boot splash"; return 0; fi
  as_root install -d "$dst"
  as_root install -m 0644 "$src/btgprojects.plymouth" "$src/btgprojects.script" "$src/logo.png" "$dst/"
  as_root update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$dst/btgprojects.plymouth" 200 >/dev/null
  as_root update-alternatives --set default.plymouth "$dst/btgprojects.plymouth" >/dev/null
  info "rebuilding the boot image (about a minute)..."
  as_root update-initramfs -u -k "$kver" >/dev/null 2>&1 || { warn "update-initramfs failed; the splash will not show. The theme files are installed."; return 1; }
  if [ "$DRY" != 1 ] && [ "$SCRATCH" != 1 ]; then
    # check the new boot image really contains the theme. The listing tool depends on the Ubuntu release (initramfs-tools:
    # lsinitramfs, dracut: lsinitrd) and the image is root-only, so ask whichever exists, as root.
    local lister n img="/boot/initrd.img-$kver"
    for lister in lsinitramfs lsinitrd; do as_root sh -c "command -v $lister" >/dev/null 2>&1 && break; lister=""; done
    if [ -z "$lister" ]; then warn "no tool found to look inside the boot image (lsinitramfs / lsinitrd), so the splash could not be verified. The theme files are installed."
    else
      n=$(as_root "$lister" "$img" 2>/dev/null | grep -c btgprojects || true)
      if [ "${n:-0}" -ge 3 ]; then ok "boot splash installed ($n entries in the boot image)"
      else warn "the splash is not inside the new boot image (found ${n:-0} entries; expected 3 or more)"; return 1; fi
    fi
  fi
  info "On Ubuntu for the Pi the new boot image is switched in after a second reboot: the splash may take two restarts to appear."
}

_login_theme() {
  local wall="$ART_DIR/brand/wallpaper-1080p.png" yaru=/usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource
  [ -f "$yaru" ] || yaru=/usr/share/gnome-shell/gnome-shell-theme.gresource
  if [ "$DRY" != 1 ] && { [ ! -f "$wall" ] || [ ! -f "$yaru" ]; }; then warn "login theme skipped (wallpaper or GNOME theme not found)"; return 0; fi
  apt_install libglib2.0-dev-bin || { warn "could not install glib-compile-resources; login theme skipped"; return 0; }
  as_root install -d -m 755 /usr/local/share/steamed-pi
  as_root install -m 644 "$wall" /usr/local/share/steamed-pi/login-bg.png
  if [ "$DRY" = 1 ]; then info "[dry-run] would build a login theme from $yaru"; return 0; fi
  local w; w=$(mktemp -d)
  _login_theme_build "$yaru" "$w"; local rc=$?; rm -rf "$w"; [ $rc = 0 ] || return 0
  # dark scheme + accent colour for the login screen
  local f=/etc/gdm3/greeter.dconf-defaults
  if [ -f "$f" ] && ! grep -q steamed-pi "$f"; then
    backup_once "$f"
    as_root sed -i "s|^# accent-color='blue'|# steamed-pi\naccent-color='yellow'\ncolor-scheme='prefer-dark'|" "$f"
  fi
  return 0
}

_login_theme_build() {      # _login_theme_build GRESOURCE WORKDIR : compile a copy of the theme with our background; install it
  local yaru=$1 w=$2
  { echo '<?xml version="1.0" encoding="UTF-8"?><gresources><gresource prefix="/org/gnome/shell/theme">'
    local r rel
    for r in $(gresource list "$yaru"); do rel=${r#/org/gnome/shell/theme/}; mkdir -p "$w/$(dirname "$rel")"; gresource extract "$yaru" "$r" > "$w/$rel"; echo "<file>$rel</file>"; done
    echo '</gresource></gresources>'; } > "$w/theme.xml"
  python3 - "$w/gdm.css" <<'PY' || { warn "could not edit the login stylesheet; login theme skipped"; return 1; }
import sys, re
p = sys.argv[1]; s = open(p).read()
new = '#lockDialogGroup {\n  background-color: #040404;\n  background-image: url("file:///usr/local/share/steamed-pi/login-bg.png");\n  background-position: center;\n  background-size: cover; }'
t = re.sub(r'#lockDialogGroup \{[^}]*\}', new, s, count=1)
if t == s: raise SystemExit(1)
open(p, 'w').write(t)
PY
  # a failed build leaves the stock login theme untouched
  if glib-compile-resources --sourcedir="$w" --target="$w/out.gresource" "$w/theme.xml" && gresource list "$w/out.gresource" | grep -q gdm.css; then
    as_root install -m 644 "$w/out.gresource" /usr/local/share/steamed-pi/gdm-theme.gresource
    as_root update-alternatives --install /usr/share/gnome-shell/gdm-theme.gresource gdm-theme.gresource /usr/local/share/steamed-pi/gdm-theme.gresource 30 >/dev/null
    ok "login screen themed"
  else warn "could not build the login theme; the stock one stays"; return 1; fi
  return 0
}
