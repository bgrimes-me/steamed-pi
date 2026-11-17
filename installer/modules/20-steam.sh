# shellcheck shell=bash
# Step "steam": download Valve's ARM64 Steam client (from Valve, never from this repo) and wire up the folders it expects.
mod_steam() {
  step "Installing Valve's native ARM64 Steam client"
  local force=(); [ "$FORCE" = 1 ] && force=(--force)
  if [ "$DRY" = 1 ]; then info "[dry-run] would run steam_fetch.py into $STEAM_DIR"
  else as_user python3 -I "$REPO_DIR/installer/steam_fetch.py" "$STEAM_DIR" "${force[@]}" || return 1; fi
  # Steam looks for itself at ~/.steam/steam and ~/.steam/root (and bin32/bin64/sdkarm64 for its overlay and SDK)
  as_user mkdir -p "$TARGET_HOME/.steam"
  local l
  for l in "steam:$STEAM_DIR" "root:$STEAM_DIR" "bin32:$STEAM_DIR/ubuntu12_32" "bin64:$STEAM_DIR/ubuntu12_64" "sdkarm64:$STEAM_DIR/linuxarm64"; do
    as_user ln -sfn "${l#*:}" "$TARGET_HOME/.steam/${l%%:*}"
  done
  ok "Steam is in $STEAM_DIR (it updates itself the first time it starts)"
}
