"""Shared helpers for the console overlay and Home-button service (X11/XWayland window tools, process pausing,
controller device access). Plain stdlib."""
import os, re, glob, subprocess, signal, time, struct, fcntl, json, ctypes

HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.cache', 'steamed-pi')
STATE = os.path.join(CACHE, 'paused.json')
os.makedirs(CACHE, exist_ok=True)

# ---------------------------------------------------------------- X11 / XWayland windows
def xenv():
    auth = sorted(glob.glob('/run/user/%d/.mutter-Xwaylandauth.*' % os.getuid()), key=os.path.getmtime)
    os.environ['DISPLAY'] = ':0'
    if auth: os.environ['XAUTHORITY'] = auth[-1]

def xprop(args):
    xenv(); return subprocess.run(['xprop'] + args, capture_output=True, text=True, timeout=3).stdout

class _XClientMessage(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                ('display', ctypes.c_void_p), ('window', ctypes.c_ulong), ('message_type', ctypes.c_ulong),
                ('format', ctypes.c_int), ('data', ctypes.c_long * 5)]

def x_activate(wid):
    """Ask the window manager to activate wid like a pager would (also un-minimizes)."""
    xenv(); x = ctypes.CDLL('libX11.so.6')
    x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XInternAtom.restype = ctypes.c_ulong; x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XDefaultRootWindow.restype = ctypes.c_ulong; x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    x.XFlush.argtypes = [ctypes.c_void_p]; x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    d = x.XOpenDisplay(b':0')
    if not d: raise RuntimeError('cannot open X display')
    ev = _XClientMessage(); ev.type = 33; ev.display = d; ev.window = wid
    ev.message_type = x.XInternAtom(d, b'_NET_ACTIVE_WINDOW', 0); ev.format = 32
    ev.data[0] = 2; ev.data[1] = 0; ev.data[2] = 0
    x.XSendEvent(d, x.XDefaultRootWindow(d), 0, (1 << 20) | (1 << 19), ctypes.byref(ev))
    x.XFlush(d); x.XCloseDisplay(d)

_SKIP = ('steam"', 'steamwebhelper', 'mutter', 'gnome-shell', 'xwayland', 'ibus', 'zenity', 'steamed-pi-overlay')

def find_game_window():
    """Topmost fullscreen window that isn't Steam's own UI. Returns (wid, area, title) or None."""
    try: ids = [int(x, 16) for x in re.findall(r'0x[0-9a-f]+', xprop(['-root', '_NET_CLIENT_LIST_STACKING']))]
    except Exception: ids = []
    for wid in reversed(ids):
        info = xprop(['-id', hex(wid), 'WM_CLASS', '_NET_WM_STATE', '_NET_WM_NAME']); low = info.lower()
        cls = re.search(r'wm_class.*', low)
        if not cls or any(k in cls.group(0) for k in _SKIP): continue
        if '_net_wm_state_fullscreen' in low:
            t = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', info)
            return (wid, 0, t.group(1) if t else '?')
    xenv(); out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True, timeout=3).stdout
    best = None
    for m in re.finditer(r'^\s+(0x[0-9a-f]+) "([^"]*)": \("steam_app_[^"]*" "steam_app_[^"]*"\)\s+(\d+)x(\d+)', out, re.M):
        wid, name, w, h = int(m.group(1), 16), m.group(2), int(m.group(3)), int(m.group(4))
        if w * h >= 640 * 360 and (best is None or w * h > best[1]): best = (wid, w * h, name)
    return best

def find_steam_window():
    """Steam's own UI window (Big Picture / main window) or None."""
    xenv(); out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True, timeout=3).stdout
    best = None
    for m in re.finditer(r'^\s+(0x[0-9a-f]+) "([^"]*)": \("steamwebhelper" "steam"\)\s+(\d+)x(\d+)', out, re.M):
        wid, name, w, h = int(m.group(1), 16), m.group(2), int(m.group(3)), int(m.group(4))
        if w * h >= 640 * 360 and (best is None or w * h > best[1]): best = (wid, w * h, name)
    return best

def window_pid(wid):
    m = re.search(r'= (\d+)', xprop(['-id', hex(wid), '_NET_WM_PID']))
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------- processes: pause / resume / close
PROTECTED = {'steam', 'steamwebhelper', 'gnome-shell', 'Xwayland', 'systemd', 'mutter-x11-fram', 'gnome-session-b',
             'labwc', 'cage', 'python3', 'steamed-pi-overlay', 'dbus-broker', 'dbus-daemon', 'pipewire', 'wireplumber'}

def _procs():
    out = {}
    for d in os.listdir('/proc'):
        if not d.isdigit(): continue
        try:
            s = open('/proc/%s/stat' % d).read()
            comm = s[s.index('(') + 1:s.rindex(')')]; rest = s[s.rindex(')') + 2:].split()
            out[int(d)] = (int(rest[1]), comm)       # ppid, comm
        except (OSError, ValueError): pass
    return out

def tree(pid):
    procs = _procs(); kids = {}
    for p, (pp, _) in procs.items(): kids.setdefault(pp, []).append(p)
    res, stack = [], [pid]
    while stack:
        p = stack.pop()
        if p in procs: res.append(p); stack.extend(kids.get(p, []))
    return [(p, procs[p][1]) for p in res]

def comm_of(pid):
    try: return open('/proc/%d/comm' % pid).read().strip()
    except OSError: return None

def pause_game(pid):
    """SIGSTOP the game process and its children (never Steam/desktop pieces). Returns the list of stopped pids."""
    if not pid or comm_of(pid) in {None} | PROTECTED: return []
    stopped = []
    for p, comm in tree(pid):
        if comm in PROTECTED: continue
        try: os.kill(p, signal.SIGSTOP); stopped.append(p)
        except OSError: pass
    json.dump(stopped, open(STATE, 'w'))
    return stopped

def resume_stopped():
    """SIGCONT everything we stopped (also recovers from a crashed overlay)."""
    try: pids = json.load(open(STATE))
    except (OSError, ValueError): pids = []
    for p in pids:
        try: os.kill(p, signal.SIGCONT)
        except OSError: pass
    try: os.remove(STATE)
    except OSError: pass
    return pids

def close_process(pid, grace=3.0):
    """Polite SIGTERM, then SIGKILL after `grace` seconds."""
    if not pid or comm_of(pid) in {None} | PROTECTED: return False
    try: os.kill(pid, signal.SIGTERM)
    except OSError: return False
    end = time.time() + grace
    while time.time() < end:
        if not os.path.exists('/proc/%d' % pid): return True
        time.sleep(0.1)
    try: os.kill(pid, signal.SIGKILL)
    except OSError: pass
    return True

# ---------------------------------------------------------------- controller devices
EV_KEY, EV_ABS = 1, 3
BTN_SOUTH, BTN_EAST, BTN_MODE = 0x130, 0x131, 0x13c
ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y = 0x00, 0x01, 0x10, 0x11
EVENT_FMT = 'llHHi'; EVENT_SIZE = struct.calcsize(EVENT_FMT)

def _has_btn_mode(fd):
    n = 0x300 // 8; buf = bytearray(n)
    try: fcntl.ioctl(fd, (2 << 30) | (n << 16) | (ord('E') << 8) | (0x20 + EV_KEY), buf, True)
    except OSError: return False
    return bool(buf[BTN_MODE // 8] & (1 << (BTN_MODE % 8)))

def dev_name(fd):
    buf = bytearray(256)
    try: fcntl.ioctl(fd, (2 << 30) | (256 << 16) | (ord('E') << 8) | 0x06, buf, True)
    except OSError: return '?'
    return bytes(buf).split(b'\0')[0].decode(errors='replace')

def open_pads():
    """Open every readable gamepad-like event device (has the Home/Guide button). Returns [(fd, path, name)]."""
    pads = []
    for p in sorted(glob.glob('/dev/input/event*')):
        try: fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError: continue
        if _has_btn_mode(fd) and 'virtual keyboard' not in dev_name(fd): pads.append((fd, p, dev_name(fd)))
        else: os.close(fd)
    return pads

def grab(fd, on=True):
    try: fcntl.ioctl(fd, 0x40044590, 1 if on else 0); return True      # EVIOCGRAB
    except OSError: return False


def session_mode():
    """'console' when the labwc console compositor is running, else 'desktop' (GNOME)."""
    return 'console' if any(c == 'labwc' for _, (_, c) in _procs().items()) else 'desktop'
