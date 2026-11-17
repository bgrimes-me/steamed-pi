# shellcheck shell=bash
# Step "session": switch on the user-level pieces: services, theme, the boot default, and the Steam startup movie.
mod_session() {
  step "Enabling Steamed Pi for $TARGET_USER"
  local s="$REPO_DIR/src" u f

  # 1. user services: enabled by creating the same symlinks `systemctl --user enable` would (works with no desktop session running)
  for f in "$s"/systemd-user/*.service; do
    u=$(basename "$f"); copy_user "$f" "$CFG_DIR/systemd/user/$u" 644
    local target; target=$(sed -n 's/^WantedBy=//p' "$f" | head -1)
    [ -n "$target" ] && as_user mkdir -p "$CFG_DIR/systemd/user/$target.wants" && as_user ln -sfn "../$u" "$CFG_DIR/systemd/user/$target.wants/$u"
  done
  have_user_bus && as_user_session systemctl --user daemon-reload >/dev/null 2>&1 && as_user_session systemctl --user start steamed-pi-controller-home.service steamed-pi-dashboard.service >/dev/null 2>&1
  ok "services enabled (dashboard, Home-button handler, mode helpers)"

  # the dashboard PIN: a fresh PIN at every start (shown in the Home menu); without this file the dashboard would have no PIN
  as_user mkdir -p "$CFG_DIR/steamed-pi/dashboard"; as_user touch "$CFG_DIR/steamed-pi/dashboard/pin-auto"

  # 2. the Steam startup movie (a still from the Steamed Pi artwork); change it any time on the Settings page
  as_user "$BIN_DIR/steamed-pi-setting" set startup_movie steamed-pi >/dev/null 2>&1 && ok "startup movie installed" || warn "could not install the startup movie (steamed-pi-setting failed)"
  # keep the logo as Steam's boot image, too (re-applied at each console start in case a Steam update restores its own)
  info "the first start of the console applies the boot image"

  # 3. the Steamed Pi desktop look. Needs a running desktop session; if there is none yet, do it at the first login instead.
  if have_user_bus && as_user_session gsettings list-schemas >/dev/null 2>&1; then
    as_user_session bash "$SP_DIR/theme/steamed-pi-theme.sh" apply >/dev/null 2>&1 && ok "desktop theme applied" || warn "desktop theme could not be applied now (it will be tried at first login)"
  else info "no desktop session running: the theme is applied at your first login"; fi
  # one-shot autostart: applies the theme at first login if it has not been applied, then removes itself
  as_user mkdir -p "$CFG_DIR/autostart"
  render "$s/desktop/steamed-pi-first-login.desktop.in" "$CFG_DIR/autostart/steamed-pi-first-login.desktop"

  # 4. start in Gaming Mode by default (change it on the Settings page, or:  steamed-pi-session-switch boot desktop)
  as_user "$BIN_DIR/steamed-pi-session-switch" boot console >/dev/null 2>&1 && ok "boot default set to Gaming Mode" || warn "could not set the boot default (set it later: steamed-pi-session-switch boot console)"
  return 0
}
