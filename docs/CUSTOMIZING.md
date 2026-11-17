# Making it yours

The "Steamed Pi" name and btgprojects logo identify the project and ship as the defaults. Everything visual is a file you can replace.
The installer never overwrites art you have swapped (use `--refresh-art` if you want it to).

| What | File to replace | Then |
|---|---|---|
| Desktop wallpaper, lock screen, login screen | `~/.local/share/steamed-pi/art/brand/wallpaper-720p.png`, `-1080p.png`, `-4k.png` | `steamed-pi-setting set look steamed-pi` (desktop and lock screen). Login screen: `sudo install -m 644 ~/.local/share/steamed-pi/art/brand/wallpaper-1080p.png /usr/local/share/steamed-pi/login-bg.png` |
| Steam startup movie | any image or `.webm` | `~/.local/share/steamed-pi/tools/make-startup-movie.sh your-image.png 4`, then restart Steam |
| Frame shown after the movie | `~/.local/share/steamed-pi/art/boot-spinner.png` (450 x 450) | re-applied at the next Gaming Mode start |
| Boot splash (OS boot) | `~/.local/share/steamed-pi/plymouth/btgprojects/logo.png` | `./install.sh --only boot-look` from the repo (rebuilds the boot image) |
| Dock "Show Applications" icon | `~/.local/share/steamed-pi/art/brand/app-grid-icon.svg` | `steamed-pi-setting set look steamed-pi` |
| "Return to Gaming Mode" icon | `~/.local/share/icons/hicolor/<size>/apps/steamed-pi-gaming-mode.png` and `scalable/apps/steamed-pi-gaming-mode.svg` | log out and in |
| Logo in the dashboard header | `~/.local/share/steamed-pi/art/brand/logo.png` (wide, transparent background, shown about 72 px high; the default is "btgprojects presents steamed pi") | reload the dashboard |
| Dashboard browser-tab icon | `~/.local/share/steamed-pi/art/brand/icon.png` (square) | reload the dashboard |

The full brand sets (logos with dark and light backgrounds, icons in every size, SVG sources) are in `assets/brand/` for reference.

## Colors
All menus, the dashboard and the terminal read one file: `~/.local/share/steamed-pi/theme/palette.conf` (accent, text, background, the 16 terminal colors, ...).
Edit it, then run `bash ~/.local/share/steamed-pi/theme/steamed-pi-theme.sh apply` and restart the dashboard (`systemctl --user restart steamed-pi-dashboard`). The console menu reads it each time it opens.
Tip: GNOME's own accent can only be one of its fixed colors; `GNOME_ACCENT` picks the closest.

## Switching the look off
`steamed-pi-setting set look ubuntu` (or `steamed-pi-theme.sh undo`) restores Ubuntu's wallpaper, colors, dock pins and prompt.

## Forking and rebranding the project itself
Replace the files in `assets/` and `src/plymouth/btgprojects/logo.png`, edit the strings "Steamed Pi" in `src/dashboard/page.html`, `README.md` and `docs/`, and the colors in `src/theme/palette.conf`, then run `./install.sh --refresh-art`.
