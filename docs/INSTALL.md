# Installing Steamed Pi

## Requirements
- **Raspberry Pi 5**, 8 GB recommended. Other Pi models are untested; the installer warns and stops unless you pass `--force`.
- **Ubuntu Desktop for the Raspberry Pi** (tested on 26.10), installed, with your user signed in. Not Ubuntu Server, not Raspberry Pi OS.
- A **4 KB-page kernel** (Ubuntu's default `raspi` kernel on the Pi 5). Valve's ARM Steam client does not run on 16 KB pages; the installer checks.
- Internet access, about 8 GB free (more for games; an NVMe drive is much faster than an SD card).
- A Steam account.
- A controller (any Xbox-style pad; Bluetooth or USB).

## Install
```bash
git clone https://github.com/bgrimes-me/steamed-pi.git
cd steamed-pi
./install.sh          # asks for your password once, for sudo
sudo reboot
```
Run it as your normal user, **not** with `sudo`. It is safe to run again: each step checks first and only does what is missing.

### Options
| | |
|---|---|
| `--dry-run` | print everything it would do, change nothing |
| `--no-emulation` | skip ES-DE, RetroArch and Dolphin |
| `--only a,b` / `--skip a,b` | run or skip named steps |
| `--yes` | do not ask questions |
| `--force` | download Steam again; continue past hardware warnings |
| `--refresh-art` | overwrite the installed artwork with the files in `assets/` |
| `--hostname NAME` | name the console NAME on the network (default `steamed-pi`, applied only on the first install) |
| `--keep-hostname` | leave the machine's current name alone |
| `--user NAME` | install for the user NAME (used by the first-boot image service; normally you run it as yourself) |

Steps, in order: `preflight`, `packages`, `steam`, `deploy`, `system`, `boot-look`, `session`, `emulation`, `finish`.
The log is `~/.cache/steamed-pi-install.log`.

## After the reboot
1. The console boots into Steam Big Picture (you see the btgprojects splash, then the Steamed Pi startup movie).
2. Steam updates itself the first time. This takes a few minutes.
3. **Sign in to Steam.**
4. Steamed Pi finishes by itself: it makes Proton Experimental (ARM64) the default for Windows games, writes Pi-friendly Proton defaults, adds an **Emulation** entry to your library, and asks Steam to install the ARM compatibility tools. Steam restarts once. Progress is in `~/.cache/steamed-pi/postlogin.log`.

   *What has been verified:* the default tool, the Proton defaults and the Emulation entry were applied correctly on a real Steam account. *What has not:* the step that downloads the compatibility tools on a machine that does not have them yet (they were already installed where this was tested). If it stalls, run `steamed-pi-postlogin` again (it asks Steam to install them again), read `~/.cache/steamed-pi/postlogin.log`, and please report what you see.

If something goes wrong there, run it by hand any time: `steamed-pi-postlogin`.

## What the installer changes
**In your home folder:** programs in `~/.local/bin`, libraries in `~/.local/lib/steamed-pi`, the app in `~/.local/share/steamed-pi`, artwork in `~/.local/share/steamed-pi/art`, Steam in `~/.local/share/Steam`, user services in `~/.config/systemd/user`, a labwc config in `~/.config/steamed-pi/labwc`, launchers in `~/.local/share/applications`.

**On the system (needs sudo; every edited file is backed up as `FILE.before-steamed-pi`):**
- packages (labwc, wlr-randr, gtk4-layer-shell, ufw, openssh-server, ...)
- `/etc/sudoers.d/steamed-pi`: a short list of specific commands that run without a password: SSH on/off, reboot, power off, start/stop the desktop-only services, restart the login manager, and the hostname helper (nothing else)
- `/usr/share/wayland-sessions/steamed-pi-console.desktop`: the "Console Mode" session
- GDM automatic login for your user (your password still works for sudo and SSH)
- `steamed-pi-desktop.target` and drop-ins: desktop-only services (snapd, cups, ...) now start only in Desktop mode
- a few overhead services disabled (apport, rsyslog, ...)
- firewall (ufw): everything incoming blocked except from private home networks to the dashboard, SSH, FTP and Steam streaming ports
- a NetworkManager hook so wired and Wi-Fi addresses both work, a sysctl so FTP can use port 21
- the boot splash (Plymouth theme + rebuilt boot image) and the login-screen theme
- the network name: set to `steamed-pi` on a first install (reach it at `steamed-pi.local`) via a small root-owned helper (`/usr/local/sbin/steamed-pi-set-hostname`) that validates the name. Change it any time: Home > Settings > Console name, the dashboard, or `steamed-pi-setting set hostname NAME`. A name you chose is never overwritten by a later install.
- lingering enabled for your user so the dashboard runs at boot
- SSH stays **off** until you switch it on.

## Undo
`./uninstall.sh` reverses the system changes and removes Steamed Pi's files. `--purge` also removes Steam, ES-DE and RetroArch. It never touches `~/ROMs` or your Steam games. It leaves your console's network name and the installed packages as they are.

## Updating
`git pull && ./install.sh`. Art you have swapped is kept (see [CUSTOMIZING.md](CUSTOMIZING.md)).
