# Troubleshooting

## I'm stuck on a screen I can't use
Any of these gets you back to the normal Ubuntu desktop:
1. **Login screen** (if it shows): click your name, then the gear icon, choose **Ubuntu**.
2. **Another device**: open the dashboard (`http://<pi-address>:8080`, PIN is in the Home menu > Console info) and press the switch-mode button (it reads *Switch to Desktop* when the console is in Gaming Mode).
3. **SSH** (turn it on from the dashboard or Settings first): `steamed-pi-session-switch desktop` switches now; `steamed-pi-session-switch boot desktop` also makes the desktop the boot default.
4. **Keyboard**: Ctrl+Alt+Backspace in Gaming Mode returns to the login screen.

Gaming Mode also switches to the desktop by itself if Steam keeps failing (Settings > *If Steam keeps failing* controls this).

## Where the logs are
| | |
|---|---|
| installer | `~/.cache/steamed-pi-install.log` |
| Gaming Mode session | `~/.cache/steamed-pi/session.log` |
| Home menu | `~/.cache/steamed-pi/overlay.log` |
| first-time Steam setup | `~/.cache/steamed-pi/postlogin.log` |
| Steam | `~/.local/share/Steam/logs/` |
| a Windows game (Proton) | add `PROTON_LOG=1` to its launch options: writes `~/steam-<appid>.log` |

## Common problems
**Steam shows a black window or takes minutes the first time.** It is updating itself (a few hundred MB). Wait; check `~/.local/share/Steam/logs/bootstrap_log.txt`.

**Everything feels slow (about 7 fps).** The console is drawing on the CPU. Check `session.log` for "render device: /dev/dri/renderD128". On the Pi 5 the GPU for 3D is `v3d` (renderD128), separate from the display controller.

**A game stops right after starting.** Read its error. `No supported FNA3D driver found` means an FNA game: add `FNA3D_FORCE_DRIVER=OpenGL` (Steamed Pi sets this by default after first-time setup). `Failed to initialize graphics` on a Unity or DirectX 11 game is the GPU limit, see [COMPATIBILITY.md](COMPATIBILITY.md).

**My controller does not work in the Home menu.** Connect it any time; it is picked up within two seconds. Bluetooth controllers pair from Steam's own Settings > Bluetooth.

**No network at start-up.** The menu shows a notice. Join Wi-Fi from Steam's Settings > Internet.

**The login screen flashes at boot.** GDM always starts it for a moment; Gaming Mode brings itself to the front within a couple of seconds, and the login screen is themed to match.

**The dashboard PIN.** A new PIN is generated every time the dashboard starts (at each boot) and is shown in Home > Console info and in the start-up popup. To use a fixed PIN instead, delete `~/.config/steamed-pi/dashboard/pin-auto` and put your own digits in `~/.config/steamed-pi/dashboard/pin`.

**Resetting Steamed Pi's settings.** Delete `~/.config/steamed-pi/settings.json`.
