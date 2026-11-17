#!/usr/bin/env python3
"""Watch every readable input device for the gamepad Home/Guide button (BTN_MODE) and react.
Passive: never grabs a device, so Steam/games are unaffected.
Action = contents of ~/.config/steamed-pi/controller/command:
  (empty / missing)  -> inject Ctrl+Alt+S via a virtual keyboard (GNOME then runs the 'Back to Steam'
                        shortcut with real-input focus rights)
  anything else      -> run that shell command"""
import os, struct, fcntl, glob, select, subprocess, time, shlex
BTN_MODE = 0x13c; EV_KEY = 1; EV_SYN = 0
CFG = os.path.expanduser('~/.config/steamed-pi/controller/command')
FMT = 'llHHi'; SZ = struct.calcsize(FMT)
def log(*a): print(*a, flush=True)


import ctypes, ctypes.util, re, sys

def _xenv():
    auth = sorted(glob.glob('/run/user/1000/.mutter-Xwaylandauth.*'), key=os.path.getmtime)
    os.environ['DISPLAY'] = ':0'
    if auth: os.environ['XAUTHORITY'] = auth[-1]

class _XClientMessage(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                ('display', ctypes.c_void_p), ('window', ctypes.c_ulong), ('message_type', ctypes.c_ulong),
                ('format', ctypes.c_int), ('data', ctypes.c_long * 5)]

def x_activate(wid):
    """Ask the window manager to activate wid like a pager would (also un-minimizes)."""
    _xenv()
    x = ctypes.CDLL('libX11.so.6')
    x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XInternAtom.restype = ctypes.c_ulong; x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XDefaultRootWindow.restype = ctypes.c_ulong; x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    x.XFlush.argtypes = [ctypes.c_void_p]; x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    d = x.XOpenDisplay(b':0')
    if not d: raise RuntimeError('cannot open X display')
    ev = _XClientMessage(); ev.type = 33  # ClientMessage
    ev.display = d; ev.window = wid; ev.message_type = x.XInternAtom(d, b'_NET_ACTIVE_WINDOW', 0); ev.format = 32
    ev.data[0] = 2; ev.data[1] = 0; ev.data[2] = 0   # source=pager, timestamp=CurrentTime
    x.XSendEvent(d, x.XDefaultRootWindow(d), 0, (1 << 20) | (1 << 19), ctypes.byref(ev))  # SubstructureRedirect|Notify
    x.XFlush(d); x.XCloseDisplay(d)

def _xprop(args):
    return subprocess.run(['xprop'] + args, capture_output=True, text=True, timeout=3).stdout

_SKIP = ('steam"', 'steamwebhelper', 'mutter', 'gnome-shell', 'xwayland', 'ibus', 'zenity')

def find_game_window():
    """Topmost fullscreen window that isn't Steam's own UI (works for Steam games, ES-DE, RetroArch...).
    Falls back to the largest steam_app_* window for windowed games. Returns (wid, area, title) or None."""
    _xenv()
    try:
        stack = _xprop(['-root', '_NET_CLIENT_LIST_STACKING'])
        ids = [int(x, 16) for x in re.findall(r'0x[0-9a-f]+', stack)]
    except Exception:
        ids = []
    for wid in reversed(ids):   # topmost first
        info = _xprop(['-id', hex(wid), 'WM_CLASS', '_NET_WM_STATE', '_NET_WM_NAME'])
        low = info.lower()
        cls = re.search(r'wm_class.*', low)
        if not cls or any(k in cls.group(0) for k in _SKIP): continue
        if '_net_wm_state_fullscreen' in low:
            t = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', info)
            return (wid, 0, t.group(1) if t else '?')
    out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True, timeout=3).stdout
    best = None
    for m in re.finditer(r'^\s+(0x[0-9a-f]+) "([^"]*)": \("steam_app_[^"]*" "steam_app_[^"]*"\)\s+(\d+)x(\d+)', out, re.M):
        wid, name, w, h = int(m.group(1), 16), m.group(2), int(m.group(3)), int(m.group(4))
        if w * h >= 640 * 360 and (best is None or w * h > best[1]): best = (wid, w * h, name)
    return best


if len(sys.argv) > 2 and sys.argv[1] == '--activate':
    x_activate(int(sys.argv[2], 16)); sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == '--find':
    print(find_game_window()); sys.exit(0)


import threading
_gen = 0
def active_window():
    _xenv()
    try:
        a = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], capture_output=True, text=True, timeout=2).stdout
        return int(a.split()[-1], 16)
    except Exception:
        return None

def guard_game(wid, my_gen, seconds=2.5):
    """After handing focus to the game, undo any attempt by Steam to take it back
    (a quick tap on Home makes Steam react after we already acted). A new press cancels this."""
    end = time.time() + seconds; redo = 0
    time.sleep(0.15)
    while time.time() < end and _gen == my_gen and redo < 5:
        cur = active_window()
        if cur is not None and cur != wid:
            log('Steam took focus back (window %s) -> re-activating game' % hex(cur)); redo += 1
            try: x_activate(wid)
            except Exception as e: log('re-activate failed:', e)
            time.sleep(0.3)
        else:
            time.sleep(0.1)

# ---- virtual keyboard (uinput) ----
KEYS = (29, 56, 31, 15)  # LEFTCTRL, LEFTALT, S, TAB
STEAM_COMBO = (29, 56, 31)
SWITCH_COMBO = (56, 15)   # Alt+Tab
def make_kbd():
    fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(fd, 0x40045564, EV_KEY)           # UI_SET_EVBIT
    for k in KEYS: fcntl.ioctl(fd, 0x40045565, k)  # UI_SET_KEYBIT
    fcntl.ioctl(fd, 0x405c5503, struct.pack('<HHHH80sI', 0x03, 0x1209, 0x0001, 1, b'steamed-pi-controller-home virtual keyboard', 0))
    fcntl.ioctl(fd, 0x5501)                        # UI_DEV_CREATE
    time.sleep(1.0)
    return fd
def ev(fd, t, c, v): os.write(fd, struct.pack(FMT, 0, 0, t, c, v))
def chord(fd, keys):
    for k in keys:
        ev(fd, EV_KEY, k, 1); ev(fd, EV_SYN, 0, 0); time.sleep(0.05)
    time.sleep(0.08)
    for k in reversed(keys):
        ev(fd, EV_KEY, k, 0); ev(fd, EV_SYN, 0, 0); time.sleep(0.05)

def steam_in_front():
    # True if the focused X window is Steam's own UI (so Home should go back to the game)
    auth = sorted(glob.glob('/run/user/1000/.mutter-Xwaylandauth.*'), key=os.path.getmtime)
    env = dict(os.environ, DISPLAY=':0', XAUTHORITY=auth[-1] if auth else '')
    try:
        a = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], env=env, capture_output=True, text=True, timeout=3).stdout
        wid = a.split()[-1]
        c = subprocess.run(['xprop', '-id', wid, 'WM_CLASS'], env=env, capture_output=True, text=True, timeout=3).stdout.lower()
        return '"steam"' in c or 'steamwebhelper' in c
    except Exception as e:
        log('front-check failed:', e); return False


# ---- overlay mode: Home opens the console menu (steamed-pi-overlay). 'classic' in ~/.config/steamed-pi/controller/mode restores the old behaviour.
MODE_FILE = os.path.expanduser('~/.config/steamed-pi/controller/mode')
OVERLAY = os.path.expanduser('~/.local/bin/steamed-pi-overlay')
_classic_until = 0
def overlay_mode():
    try: m = open(MODE_FILE).read().strip() or 'overlay'
    except OSError: m = 'overlay'
    return 'classic' if (m == 'classic' or time.time() < _classic_until or not os.path.exists(OVERLAY)) else 'overlay'
def _watch_overlay(proc):
    global _classic_until
    t0 = time.time(); rc = proc.wait()
    if rc != 0 and time.time() - t0 < 6:
        log('overlay failed (rc %s) -> using the classic Home behaviour for 5 minutes' % rc); _classic_until = time.time() + 300
def launch_overlay():
    env = dict(os.environ, WAYLAND_DISPLAY='wayland-0', DISPLAY=':0', XDG_RUNTIME_DIR='/run/user/%d' % os.getuid())
    try: proc = subprocess.Popen([OVERLAY], env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e: log('cannot start overlay:', e); return False
    threading.Thread(target=_watch_overlay, args=(proc,), daemon=True).start(); log('overlay opened (pid %d)' % proc.pid); return True

kbd = None; kbd_err = None
def ensure_kbd():
    global kbd, kbd_err
    if kbd is not None: return
    try: kbd = make_kbd(); kbd_err = None; log('virtual keyboard ready')
    except Exception as e:
        if str(e) != kbd_err: log('virtual keyboard unavailable (will retry):', e)
        kbd_err = str(e)
ensure_kbd()

# ---- device discovery ----
def has_btn_mode(fd):
    n = 0x300 // 8; buf = bytearray(n)
    try: fcntl.ioctl(fd, (2 << 30) | (n << 16) | (ord('E') << 8) | (0x20 + EV_KEY), buf, True)
    except OSError: return False
    return bool(buf[BTN_MODE // 8] & (1 << (BTN_MODE % 8)))
def dev_name(fd):
    buf = bytearray(256)
    try: fcntl.ioctl(fd, (2 << 30) | (256 << 16) | (ord('E') << 8) | 0x06, buf, True)
    except OSError: return '?'
    return bytes(buf).split(b'\0')[0].decode(errors='replace')
fds = {}; last = 0
def rescan():
    for p in glob.glob('/dev/input/event*'):
        if p in fds.values(): continue
        try: fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError: continue
        if has_btn_mode(fd) and 'steamed-pi-controller-home' not in dev_name(fd): fds[fd] = p; log('watching', p, dev_name(fd))
        else: os.close(fd)
log('steamed-pi-controller-home started')
tick = 0
while True:
    if tick % 6 == 0: rescan(); ensure_kbd()
    tick += 1
    if not fds: time.sleep(2); continue
    r, _, _ = select.select(list(fds), [], [], 0.5)
    for fd in r:
        try: data = os.read(fd, SZ * 32)
        except OSError:
            log('lost', fds.pop(fd)); os.close(fd); continue
        for i in range(0, len(data) - SZ + 1, SZ):
            _, _, t, c, v = struct.unpack(FMT, data[i:i + SZ])
            if t == EV_KEY and c == BTN_MODE and v == 1:
                now = time.time(); log('HOME pressed on', fds.get(fd))
                if now - last < 0.5: continue
                last = now; _gen += 1
                if overlay_mode() == 'overlay' and launch_overlay(): continue
                cmd = ''
                try: cmd = open(CFG).read().strip()
                except OSError: pass
                if cmd:
                    log('running:', cmd)
                    try: subprocess.Popen(shlex.split(cmd), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception as e: log('error:', e)
                elif kbd is not None or (ensure_kbd() or kbd is not None):
                    if steam_in_front():
                        g = None
                        try: g = find_game_window()
                        except Exception as e: log('find game failed:', e)
                        if g:
                            log('Steam is in front -> activating game window', hex(g[0]), g[2])
                            try:
                                x_activate(g[0])
                                threading.Thread(target=guard_game, args=(g[0], _gen), daemon=True).start()
                            except Exception as e: log('activate failed:', e); chord(kbd, SWITCH_COMBO)
                        else:
                            log('Steam is in front, no game window -> Alt+Tab'); chord(kbd, SWITCH_COMBO)
                    else:
                        log('injecting Ctrl+Alt+S (open Steam)'); chord(kbd, STEAM_COMBO)
                else: log('no action available')
