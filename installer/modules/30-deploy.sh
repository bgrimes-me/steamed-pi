# shellcheck shell=bash
# Step "deploy": put the Steamed Pi programs, libraries, dashboard, theme and art in the user's home folder.
mod_deploy() {
  step "Installing Steamed Pi files for $TARGET_USER"
  local s="$REPO_DIR/src" f n
  for f in "$s"/bin/*; do [ -f "$f" ] || continue; copy_user "$f" "$BIN_DIR/$(basename "$f")" 755; done
  for f in "$s"/lib/*.py; do copy_user "$f" "$LIB_DIR/$(basename "$f")" 644; done
  for f in "$s"/dashboard/*; do [ -f "$f" ] || continue; copy_user "$f" "$SP_DIR/dashboard/$(basename "$f")" 644; done
  copy_user "$s/theme/palette.conf" "$SP_DIR/theme/palette.conf" 644
  copy_user "$s/theme/steamed-pi-theme.sh" "$SP_DIR/theme/steamed-pi-theme.sh" 755
  copy_user "$s/tools/make-startup-movie.sh" "$SP_DIR/tools/make-startup-movie.sh" 755
  for f in "$s"/plymouth/btgprojects/*; do [ -f "$f" ] || continue; copy_user "$f" "$SP_DIR/plymouth/btgprojects/$(basename "$f")" 644; done
  for f in "$REPO_DIR"/tools/*; do [ -f "$f" ] && copy_user "$f" "$BIN_DIR/$(basename "$f")" 755; done
  ok "programs and libraries installed"

  # config files that contain the user's home folder
  render "$s/labwc/rc.xml.in" "$CFG_DIR/steamed-pi/labwc/rc.xml"
  render "$s/desktop/steam-native.desktop.in" "$TARGET_HOME/.local/share/applications/steam-native.desktop"
  render "$s/desktop/steamed-pi-gaming-mode.desktop.in" "$TARGET_HOME/.local/share/applications/steamed-pi-gaming-mode.desktop"

  # the art: project identification, and the thing a user swaps to re-brand (see docs/CUSTOMIZING.md)
  local a="$REPO_DIR/assets"
  for n in wallpaper-720p.png wallpaper-1080p.png wallpaper-4k.png logo.png icon.png favicon.png logo-mark.svg logo-mark-square.svg app-grid-icon.svg cursor.ico; do
    [ -f "$ART_DIR/brand/$n" ] && [ "$FORCE" != 1 ] && [ "${REFRESH_ART:-0}" != 1 ] && continue            # never overwrite art the user has already swapped
    copy_user "$a/$n" "$ART_DIR/brand/$n" 644
  done
  [ -f "$ART_DIR/startup/startup.webm" ] && [ "$FORCE" != 1 ] && [ "${REFRESH_ART:-0}" != 1 ] || copy_user "$a/startup.webm" "$ART_DIR/startup/startup.webm" 644
  [ -f "$ART_DIR/boot-spinner.png" ] && [ "$FORCE" != 1 ] && [ "${REFRESH_ART:-0}" != 1 ] || copy_user "$a/boot-spinner.png" "$ART_DIR/boot-spinner.png" 644
  copy_user "$a/black.webm" "$ART_DIR/black.webm" 644
  for n in 32 48 64 96 128 256; do copy_user "$a/icons/steamed-pi-gaming-mode-$n.png" "$TARGET_HOME/.local/share/icons/hicolor/${n}x${n}/apps/steamed-pi-gaming-mode.png" 644; done
  copy_user "$a/logo-mark-square.svg" "$TARGET_HOME/.local/share/icons/hicolor/scalable/apps/steamed-pi-gaming-mode.svg" 644
  # the Steam icon comes from Valve's own download once Steam has run once (see steamed-pi-postlogin)
  ok "art installed in $ART_DIR"
  return 0
}
