# Third-party software and trademarks

Steamed Pi is an installer and a set of scripts. It does **not** contain, and never redistributes, any of the following.
They are downloaded from their publishers at install time, under their own licenses:

| Software | Source | Notes |
|---|---|---|
| Steam client (ARM64) and Steam's Proton / Steam Linux Runtime / FEX tools | Valve (`client-update.steamstatic.com`, then Steam itself) | Subject to the Steam Subscriber Agreement. The download is verified against Valve's own manifest. |
| ES-DE (EmulationStation Desktop Edition) | es-de.org / its GitLab releases | See the project's license. |
| RetroArch and libretro cores | libretro (`buildbot.libretro.com`) | Each core has its own license. |
| Dolphin | Ubuntu package `dolphin-emu` | |
| labwc, GNOME, Plymouth, ufw, OpenSSH, ... | Ubuntu packages | |

"Steam" and the Steam logo are trademarks of Valve Corporation. Raspberry Pi is a trademark of Raspberry Pi Ltd. This project is not affiliated with or endorsed by either.

**ROMs and BIOS files are not provided and not downloaded.** Use only games you own or are licensed to use.

## Branding
The name "Steamed Pi", the btgprojects logo and the artwork in `assets/` identify this project. They are included so the project looks right out of the box and are easy to replace ([docs/CUSTOMIZING.md](docs/CUSTOMIZING.md)).
