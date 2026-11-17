# How Steamed Pi works

## Two sessions, one login manager
GDM logs you in automatically. Which session it starts is the account's **Session** setting (AccountsService):
- `ubuntu`: normal GNOME desktop (**Desktop mode**)
- `steamed-pi-console`: our minimal session (**Gaming Mode**), registered in `/usr/share/wayland-sessions/steamed-pi-console.desktop`

`steamed-pi-session-switch console|desktop` sets that value over D-Bus and restarts GDM (one passwordless sudo rule). `steamed-pi-session-switch boot X` stores the *boot default* (`~/.config/steamed-pi/boot-mode`), which is re-applied at each login so a one-off switch is forgotten at the next reboot.

## Gaming Mode
`steamed-pi-console-session` finds the Pi's 3D GPU (`v3d`, renderD128; the display controller `vc4` cannot render) and exports `WLR_RENDER_DRM_DEVICE` so the compositor uses it, then starts **labwc** with `steamed-pi-console-start`, which:
1. imports the session environment into the user manager and stops stale desktop portals,
2. applies the *Gaming Mode screen* setting (720p by default; the Pi's GPU is the limit),
3. restarts `steamed-pi-controller-home` and starts the attention popup service,
4. starts `steamed-pi-postlogin --auto` in the background (finishes setup after your first Steam sign-in),
5. runs the **supervisor** in the foreground.

The **supervisor** (`steamed-pi-steam-supervisor`) keeps Steam running like a Steam Deck: close Steam and it restarts. If Steam fails more than three times in ten minutes it writes a notice and switches to Desktop mode (or keeps retrying, per Settings), so you are never stuck. It exits quietly when its compositor is gone.

GDM briefly starts its login screen at boot whatever you configure. `steamed-pi-console-session` therefore watches for a minute and brings Gaming Mode back to the front (`loginctl activate`) if it was covered.

## The Home menu
`steamed-pi-controller-home.py` watches the pad's Home button through evdev and, via a virtual keyboard (uinput), asks the right thing to happen. In Gaming Mode it starts **`steamed-pi-overlay`**, a GTK4 window drawn on the layer-shell *overlay* layer. The overlay pauses the game (SIGSTOP), grabs the controller (EVIOCGRAB) while open, and resumes the game when it closes. It rescans for controllers every two seconds, so a pad connected later works.

The **Settings page** is a thin layer over `steamed_pi_settings.py`, which is also what the `steamed-pi-setting` command uses. Each setting has a getter, a setter and a hint. Most reuse existing tools (`steamed-pi-session-switch`, the dashboard's local API, `steamed-pi-theme.sh`).

## First-time Steam setup
`steamed-pi-postlogin --auto` is started at every Gaming Mode start. It waits until a Steam account is signed in, then (once) closes Steam, sets the default compatibility tool to Proton Experimental (ARM64) in `config.vdf`, adds an *Emulation* shortcut for ES-DE to `shortcuts.vdf` (Steam must be closed to edit those), restarts Steam, asks it to install the ARM compatibility tools with `steam://install/...`, and writes Proton's `user_settings.py` (WineD3D, OpenGL for FNA games). On later starts it only re-writes the Proton defaults, since a Proton update can remove them. Its markers are in `~/.local/state/steamed-pi`.

## Dashboard
`dashboard/server.py` is a small standard-library HTTP server on port 8080, reachable only from private networks. State-changing requests need a header that only the dashboard page sets (CSRF) and the PIN. It reports status and runs: SSH/FTP on/off, restart Steam, close game, reboot, power off, switch mode. SSH goes through `systemctl` (sudo rule); FTP is an in-process `pyftpdlib` server serving `~/ROMs` with a random password.

## Network name
`system/steamed-pi-set-hostname` is installed root-owned in `/usr/local/sbin` and is the only hostname command the sudo rule allows. It validates the name (letters, digits, hyphens), runs `hostnamectl`, updates the `127.0.1.1` line of `/etc/hosts`, stops cloud-init putting the old name back, and restarts avahi so `NAME.local` follows. The installer, the dashboard and the Settings page all call it.

## Keeping the console lean
`steamed-pi-desktop.target` lists services only Desktop mode needs. Each gets `PartOf=steamed-pi-desktop.target`; a user service tied to the GNOME session starts the target at login and stops it at logout. Leftover GNOME helper services are stopped when Gaming Mode starts.

## Steam
`installer/steam_fetch.py` downloads Valve's `bins_linuxarm64_linuxarm64` package from Valve's public manifest, checks size and SHA-256, and unpacks it to `~/.local/share/Steam`. The client then updates itself. The `steam` wrapper runs `./steam -deckard -steamos3 ...` (the ARM64 backend) and restarts on exit code 42 (self-update).

## Layout of this repository
```
install.sh, uninstall.sh      entry points
installer/                    lib.sh, one module per step (modules/NN-name.sh), steam_fetch.py
src/bin, src/lib              commands and Python libraries   -> ~/.local/bin, ~/.local/lib/steamed-pi
src/dashboard, theme, plymouth, tools   -> ~/.local/share/steamed-pi
src/systemd-user, labwc, desktop        templates (@HOME@/@USER@ filled in at install)
src/emulation                 ES-DE override, RetroArch config patcher
system/                       root-owned templates (sudoers, desktop target, network hook)
assets/                       branding: wallpapers, logo, icons, startup movie; assets/brand has the full brand sets
tools/compat                  game-compatibility predictor
tools/dev                     developer-only helpers (not installed)
tests/smoke.sh                checks that need no Pi
image/                        experimental flash-and-go image support
```
