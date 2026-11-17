# shellcheck shell=bash
# Step "emulation" (optional: --no-emulation skips it): ES-DE front end, RetroArch + cores, Dolphin.
# Everything is downloaded from the projects' own sites at install time; none of it is stored in this repository.
# ROMs and BIOS files are NOT provided: put your own legally obtained games in ~/ROMs/<system>/ and BIOS files in ~/ROMs/bios/.
CORES=(gambatte mgba nestopia snes9x genesis_plus_gx desmume mupen64plus_next parallel_n64 flycast pcsx_rearmed ppsspp)

mod_emulation() {
  step "Emulation: ES-DE, RetroArch, Dolphin"
  apt_install retroarch retroarch-assets libretro-core-info dolphin-emu 7zip || return 1
  local app="$TARGET_HOME/Applications" rc=0
  as_user mkdir -p "$app" "$TARGET_HOME/ROMs/bios"
  _emu_esde "$app" || rc=1
  _emu_retroarch "$app" || rc=1
  _emu_cores || rc=1
  # configuration
  if [ "$DRY" != 1 ]; then
    as_user python3 -I "$REPO_DIR/src/emulation/retroarch-config.py" "$CFG_DIR/retroarch/retroarch.cfg" >/dev/null && ok "RetroArch configured (hotkeys: hold Select, then Start = quit, R1/L1 = save/load, X = menu)"
    copy_user "$REPO_DIR/src/emulation/es_systems.xml" "$TARGET_HOME/ES-DE/custom_systems/es_systems.xml" 644
  fi
  return $rc
}

_emu_esde() {
  local dir="$1/ES-DE"
  if [ -x "$dir/squashfs-root/AppRun" ] && [ "$FORCE" != 1 ]; then ok "ES-DE already installed"; return 0; fi
  [ "$DRY" = 1 ] && { info "[dry-run] would download the latest ES-DE aarch64 AppImage from es-de.org's GitLab"; return 0; }
  info "finding the latest ES-DE release..."
  local url; url=$(python3 -I - <<'PY'
import json, urllib.request
req = urllib.request.Request('https://gitlab.com/api/v4/projects/es-de%2Femulationstation-de/releases?per_page=5', headers={'User-Agent': 'steamed-pi-installer'})
for r in json.load(urllib.request.urlopen(req, timeout=60)):
    for l in r.get('assets', {}).get('links', []):
        if l['name'] == 'ES-DE_aarch64.AppImage': print(l['url']); raise SystemExit
PY
)
  [ -n "$url" ] || { warn "could not find an ES-DE aarch64 release; skipping ES-DE"; return 1; }
  as_user mkdir -p "$dir"
  as_user curl -fL --retry 3 -o "$dir/ES-DE_aarch64.AppImage" "$url" || { warn "ES-DE download failed"; return 1; }
  as_user chmod +x "$dir/ES-DE_aarch64.AppImage"
  ( cd "$dir" && as_user "$dir/ES-DE_aarch64.AppImage" --appimage-extract >/dev/null 2>&1 )      # unpack instead of mounting: needs no FUSE
  [ -x "$dir/squashfs-root/AppRun" ] && ok "ES-DE installed" || { warn "could not unpack ES-DE"; return 1; }
}

_emu_retroarch() {
  local dir="$1/RetroArch-nightly"
  if [ -x "$dir/retroarch" ] && [ "$FORCE" != 1 ]; then ok "RetroArch (nightly) already installed"; return 0; fi
  [ "$DRY" = 1 ] && { info "[dry-run] would download the RetroArch nightly (aarch64)"; return 0; }
  local w rc; w=$(mktemp -d)
  _emu_retroarch_fetch "$dir" "$w"; rc=$?; rm -rf "$w"; return $rc
}

_emu_retroarch_fetch() {     # _emu_retroarch_fetch INSTALL_DIR WORKDIR
  local dir=$1 w=$2
  # Ubuntu's own RetroArch is OpenGL-ES only; the nightly build has desktop OpenGL, which the N64/Dreamcast/PSP cores need
  curl -fL --retry 3 -o "$w/ra.7z" https://buildbot.libretro.com/nightly/linux/aarch64/RetroArch.7z || { warn "RetroArch nightly download failed; the Ubuntu package will be used"; return 1; }
  ( cd "$w" && 7z x -y ra.7z >/dev/null ) || { warn "could not unpack RetroArch"; return 1; }
  local bin; bin=$(find "$w" -type f -name retroarch -perm -u+x | head -1); [ -n "$bin" ] || bin=$(find "$w" -type f -name retroarch | head -1)
  [ -n "$bin" ] || { warn "no retroarch program in the nightly archive"; return 1; }
  as_user mkdir -p "$dir"; as_user cp -f "$bin" "$dir/retroarch"; as_user chmod +x "$dir/retroarch"; ok "RetroArch (nightly) installed"
}

_emu_cores() {
  local cdir="$CFG_DIR/retroarch/cores" c n=0
  as_user mkdir -p "$cdir"
  [ "$DRY" = 1 ] && { info "[dry-run] would download ${#CORES[@]} libretro cores into $cdir"; return 0; }
  for c in "${CORES[@]}"; do
    [ -f "$cdir/${c}_libretro.so" ] && [ "$FORCE" != 1 ] && { n=$((n+1)); continue; }
    local z; z=$(mktemp)
    if curl -fsL --retry 3 -o "$z" "https://buildbot.libretro.com/nightly/linux/aarch64/latest/${c}_libretro.so.zip" && unzip -oq "$z" -d "$cdir"; then n=$((n+1)); else warn "core $c could not be downloaded"; fi
    rm -f "$z"
  done
  as_user chown -R "$TARGET_USER:$TARGET_USER" "$cdir" 2>/dev/null || true
  ok "$n of ${#CORES[@]} emulator cores in place"; [ "$n" -ge $((${#CORES[@]}-2)) ]
}
