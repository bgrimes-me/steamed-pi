# A "flash and go" image (experimental)

**Status: experimental and untested on real hardware.** The supported, tested route is: flash stock Ubuntu Desktop for the Pi, then run `./install.sh` ([INSTALL.md](INSTALL.md)).

## What an image can and cannot be
An image cannot be completely finished before first boot:
- **Valve's Steam client cannot be redistributed**, so every install downloads it from Valve.
- ES-DE, RetroArch and the libretro cores are downloaded from their authors, too.
- The user account does not exist until you complete Ubuntu's setup wizard, and the installer needs it (automatic login, ownership of files).

So the image is **stock Ubuntu with Steamed Pi pre-staged** in `/opt/steamed-pi` and a first-boot service that runs the installer for you once the account exists and the network is up. You skip `git clone` and the terminal. The first boot needs internet.

## Building it
On a Linux machine (an ARM64 machine, including a Pi, avoids emulation), as root:

```bash
sudo image/build-image.sh --base ubuntu-desktop-raspi.img.xz --out steamed-pi.img
```
Then flash `steamed-pi.img` with Raspberry Pi Imager ("Use custom"). Boot, complete Ubuntu's setup, and wait. When the installer finishes (this takes a while, mostly downloading) it reboots into Gaming Mode by itself. Progress is in `/var/log/steamed-pi-firstboot.log`.

## What is not done yet
- It has not been run end to end. Expect to debug the first-boot timing (waiting for the setup wizard to finish).
- Publishing a ready-made image file would still contain no Valve software, but check the licenses of anything else you add.
- A tested release would pin the base image version and checksum.
