# Which games run on a Raspberry Pi 5?

Short version: **older, lighter and 2D games run; modern 3D and DirectX 11/12 games do not.** Steamed Pi cannot change that, but it can tell you which games in your library are worth trying.

## What decides it
1. **Direct3D version.** DirectX 9 and older run through WineD3D. DirectX 10 stated on a store page is usually fine for 2D engines. DirectX 11 and 12 need DXVK, and the Pi 5's Vulkan driver (V3DV) lacks a feature DXVK requires (`multiDrawIndirect`), so those games fail with "Failed to initialize graphics". That includes nearly every Unity game (its Windows builds ship only D3D11/12 shaders).
2. **OpenGL.** Up to about 3.x works through the Pi's driver. 4.x does not.
3. **Valve's ARM rating.** Steam stores a verified / playable / unsupported rating for ARM hardware (made for the Steam Frame, which is not a Pi, so it is a hint, not a promise).
4. **How heavy.** 2D, pixel-art, card, puzzle and older games are fine. 3D is a gamble even when old. Anything wanting a modern GPU or 8 GB or more is out.
5. **Never:** VR, online-only and anti-cheat games.

Native Linux (x86) builds do not launch: Steam's FEX tool needs a SteamOS root filesystem that does not exist here. Steamed Pi runs the **Windows** version through Proton Experimental (ARM64) instead.

## Settings that make Windows games work
After you sign in, `steamed-pi-postlogin` sets Proton's defaults for the Pi (in each Proton tool's `user_settings.py`):

```
PROTON_USE_WINED3D=1        use WineD3D (OpenGL) instead of DXVK
FNA3D_FORCE_DRIVER=OpenGL   FNA games (Celeste, FEZ, Terraria, Duck Game, ...) otherwise stop with "No supported FNA3D driver found"
```
You can also set them per game in Steam's launch options: `FNA3D_FORCE_DRIVER=OpenGL PROTON_USE_WINED3D=1 %command%`.

## Known results (from the author's Pi 5, 8 GB)
| Result | Games |
|---|---|
| Works well | Celeste, FEZ, Owlboy, Stardew Valley, Terraria, Sonic Mania, Super Meat Boy, 80's OVERDRIVE |
| Fails | The Binding of Isaac: Rebirth (black window; Valve rates it ARM-unsupported); Windows Unity games ("Failed to initialize graphics") |
| Fixed by the settings above, not fully verified | Duck Game |
| Works from the desktop, fails in Gaming Mode, being investigated | Magicka |

Please send results: an issue with the game, what you set, and what happened helps everyone.

## Check your own library
```bash
tools/compat/run.sh
```
It reads which games you own from Steam's local files, asks Valve's public store API for each game's stated requirements (one request per game, about 35 minutes for 1,000 games, and nothing else is sent), and writes `~/.cache/steamed-pi/compat/TEST-LIST.md` and `library-compat.csv`: every game as *Try first*, *Worth testing*, *Blocked (DXVK)* or *No*, with the reason.
Add the Steam app ids of games you have confirmed to `confirmed.txt` in that folder and re-run with `--quick`.

The tool is a prediction. The DirectX version is what the store page *says*, not what the game uses, and Steam has no "engine" field, so some games will surprise you.

## Games that need no translation
PCGamingWiki keeps a [list of games with native Linux ARM builds](https://www.pcgamingwiki.com/wiki/List_of_Linux_ARM_games), mostly free and open source (SuperTuxKart, OpenTTD, Endless Sky, Shattered Pixel Dungeon, ...), and several classic-game engines run from your own game files (Quake, Duke Nukem 3D, Diablo via devilutionX, OpenMW, ...).
