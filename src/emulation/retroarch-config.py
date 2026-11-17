#!/usr/bin/python3 -I
"""Set the RetroArch options Steamed Pi relies on, leaving every other option as it is.
    retroarch-config.py [PATH_TO_retroarch.cfg]
Hotkeys are tuned for Xbox-style pads (what Steam presents): hold Select, then Start = quit, R1 = save state,
L1 = load state, X = RetroArch menu. (The console menu's Home button is separate.)"""
import os, re, sys
home = os.path.expanduser('~')
path = sys.argv[1] if len(sys.argv) > 1 else home + '/.config/retroarch/retroarch.cfg'
want = {
    'input_enable_hotkey_btn': '6', 'input_exit_emulator_btn': '7', 'input_save_state_btn': '5', 'input_load_state_btn': '4', 'input_menu_toggle_btn': '2',
    'video_driver': 'gl', 'video_fullscreen': 'true', 'video_windowed_fullscreen': 'true', 'audio_driver': 'pulse', 'input_joypad_driver': 'udev',
    'config_save_on_exit': 'true', 'savestate_auto_save': 'false', 'savestate_auto_load': 'false',
    'system_directory': home + '/ROMs/bios', 'libretro_directory': home + '/.config/retroarch/cores',
    'libretro_info_path': '/usr/share/libretro/info', 'assets_directory': '/usr/share/libretro/assets',
}
os.makedirs(os.path.dirname(path), exist_ok=True)
text = open(path).read() if os.path.exists(path) else ''
for k, v in want.items():
    line = '%s = "%s"' % (k, v)
    if re.search(r'^%s\s*=' % re.escape(k), text, re.M): text = re.sub(r'^%s\s*=.*$' % re.escape(k), line, text, count=1, flags=re.M)
    else: text += ('' if text.endswith('\n') or not text else '\n') + line + '\n'
open(path, 'w').write(text); print('RetroArch configured:', path)
