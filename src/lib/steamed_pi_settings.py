"""Steamed Pi settings: one place that knows how to read and change every user-adjustable option.
Used by the console menu (Settings page) and by `steamed-pi-setting` (command line). Every setting has:
    key, label, options [(value, shown text)], hint, get() -> value, set(value) -> (ok, message)
Small choices live in ~/.config/steamed-pi/settings.json; the rest reuse the tools we already built
(steamed-pi-session-switch, the dashboard's local API, steamed-pi-theme.sh, ...)."""
import os, re, json, secrets, socket, subprocess, urllib.request, urllib.error, glob

HOME = os.path.expanduser('~')
CFG = HOME + '/.config/steamed-pi'; SETTINGS_FILE = CFG + '/settings.json'
DASH = HOME + '/.config/steamed-pi/dashboard'
BIN = HOME + '/.local/bin'
MOVIE_NAMES = ['steam_os_startup', 'bigpicture_startup', 'steam_os_family_startup', 'startup_machine', 'deck_startup', 'oled_startup', 'steamframe_startup_450x450']
MOVIE_DIR = HOME + '/.local/share/Steam/config/uioverrides/movies'
MASTER = HOME + '/.local/share/steamed-pi/art/startup/startup.webm'
BLACK = HOME + '/.local/share/steamed-pi/art/black.webm'
THEME = HOME + '/.local/share/steamed-pi/theme/steamed-pi-theme.sh'
DRY = bool(os.environ.get('STEAMED_PI_SETTINGS_DRY'))

def _load():
    try: return json.load(open(SETTINGS_FILE))
    except (OSError, ValueError): return {}
def _save(d):
    os.makedirs(CFG, exist_ok=True); tmp = SETTINGS_FILE + '.tmp'; json.dump(d, open(tmp, 'w'), indent=1); os.replace(tmp, SETTINGS_FILE)
def stored(key, default): return _load().get(key, default)
def store(key, value): d = _load(); d[key] = value; _save(d)
def run(cmd, timeout=40, env=None):
    if DRY: return 0, '(dry) ' + ' '.join(cmd)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env); return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e: return 1, str(e)

# ---------------------------------------------------------------- dashboard API (SSH / FTP / address preference)
def _pin():
    try: return open(DASH + '/pin').read().strip()
    except OSError: return ''
def dash_status():
    try: return json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/status', timeout=2))
    except Exception: return None
def dash_action(name, **params):
    if DRY: return True, '(dry) ' + name
    req = urllib.request.Request('http://127.0.0.1:8080/api/action', data=json.dumps(dict(params, name=name)).encode(),
                                 headers={'X-Dashboard': '1', 'X-Pin': _pin(), 'Content-Type': 'application/json'})
    try: r = json.load(urllib.request.urlopen(req, timeout=15)); return bool(r.get('ok')), r.get('message', '')
    except urllib.error.HTTPError as e: return False, 'dashboard said %s' % e.code
    except Exception as e: return False, 'dashboard is not responding'

# ---------------------------------------------------------------- individual settings
def get_boot():
    try: v = open(CFG + '/boot-mode').read().strip()
    except OSError: v = ''
    return v if v in ('console', 'desktop') else 'console'
def set_boot(v):
    rc, out = run([BIN + '/steamed-pi-session-switch', 'boot', v]); return rc == 0, ('Will start in %s' % ('Gaming Mode' if v == 'console' else 'Desktop')) if rc == 0 else out[-120:]

DISPLAY_MODES = {'720p': ('1280x720@60Hz', '1280x720'), '1080p': ('1920x1080@60Hz', '1920x1080')}
def get_display(): v = stored('display', '720p'); return v if v in ('720p', '1080p', 'native') else '720p'
def apply_display(v, quiet=False):
    """Apply the screen mode to the running compositor (console mode only). Returns (ok, message)."""
    out = subprocess.run(['wlr-randr'], capture_output=True, text=True).stdout if not DRY else ''
    m = re.match(r'(\S+)', out); name = m.group(1) if m else None
    if not name: return False, 'No screen found (only works in Gaming Mode)'
    if v == 'native':
        rc, o = run(['wlr-randr', '--output', name, '--preferred']); return rc == 0, 'Using the monitor’s best mode' if rc == 0 else 'Could not change the screen mode'
    for mode in DISPLAY_MODES[v]:
        if mode.split('@')[0] in out:
            rc, o = run(['wlr-randr', '--output', name, '--mode', mode])
            if rc == 0: return True, 'Screen set to %s' % mode
    return False, 'This monitor does not offer %s' % v
def set_display(v):
    store('display', v)
    ok, msg = apply_display(v)
    return True, msg if ok else 'Saved. Applies when Gaming Mode starts'

def get_movie():
    v = stored('startup_movie', 'steamed-pi'); return v if v in ('steamed-pi', 'none', 'steam') else 'steamed-pi'
def apply_movie(v):
    os.makedirs(MOVIE_DIR, exist_ok=True)
    for n in MOVIE_NAMES:
        dst = '%s/%s.webm' % (MOVIE_DIR, n)
        if v == 'steam':
            try: os.remove(dst)
            except OSError: pass
        else:
            src = MASTER if v == 'steamed-pi' else BLACK
            if not os.path.exists(src): return False, 'Missing %s' % os.path.basename(src)
            with open(src, 'rb') as a, open(dst + '.tmp', 'wb') as b: b.write(a.read())
            os.replace(dst + '.tmp', dst)
    return True, ''
def set_movie(v):
    ok, msg = apply_movie(v) if not DRY else (True, '')
    if not ok: return False, msg
    store('startup_movie', v); return True, 'Saved. Shows the next time Steam starts'

def get_popups(): v = stored('popups', 'normal'); return v if v in ('normal', 'quiet') else 'normal'
def set_popups(v): store('popups', v); return True, 'Saved'

def get_safety(): v = stored('safety', 'desktop'); return v if v in ('desktop', 'retry') else 'desktop'
def set_safety(v): store('safety', v); return True, 'Saved'

def get_ssh(): st = dash_status(); return ('on' if st and st['ssh']['on'] else 'off') if st else 'off'
def set_ssh(v): ok, m = dash_action('ssh_on' if v == 'on' else 'ssh_off'); return ok, m or 'Done'
def get_ftp(): st = dash_status(); return ('on' if st and st['ftp']['on'] else 'off') if st else 'off'
def set_ftp(v): ok, m = dash_action('ftp_on' if v == 'on' else 'ftp_off'); return ok, m or 'Done'

def get_iface():
    try: v = json.load(open(DASH + '/prefs.json')).get('iface', 'auto')
    except (OSError, ValueError): v = 'auto'
    return v if v in ('auto', 'wired', 'wifi') else 'auto'
def set_iface(v): return dash_action('set_iface', value=v)

HOSTNAME_HELPER = '/usr/local/sbin/steamed-pi-set-hostname'
HOSTNAME_RE = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')
def get_hostname(): return socket.gethostname()
def set_hostname(v):
    v = (v or '').strip().lower()
    if not HOSTNAME_RE.match(v): return False, 'Use 1-63 letters, digits and hyphens, not starting or ending with a hyphen'
    if v == get_hostname(): return True, 'Already named %s' % v
    rc, out = run(['sudo', '-n', HOSTNAME_HELPER, v])
    if rc != 0: return False, (out or 'Could not change the name')[-120:]
    try: os.makedirs(CFG, exist_ok=True); open(CFG + '/hostname-chosen', 'w').close()
    except OSError: pass
    return True, 'Named %s. Reach it at %s.local (other devices need the new name)' % (v, v)

def get_look():
    rc, out = run(['gsettings', 'get', 'org.gnome.desktop.background', 'picture-uri']) if not DRY else (0, '')
    return 'steamed-pi' if 'wallpaper-' in out or 'steamed' in out else 'ubuntu'
def set_look(v):
    rc, out = run([THEME, 'apply' if v == 'steamed-pi' else 'undo'], timeout=90) if not DRY else (0, '')
    if rc != 0:
        rc, out = run(['bash', THEME, 'apply' if v == 'steamed-pi' else 'undo'], timeout=90)
    return rc == 0, 'Desktop look changed (shows in Desktop mode)' if rc == 0 else out[-120:]

def get_pin(): return _pin() or 'not set'
def set_pin(_v=None):
    new = ''.join(secrets.choice('0123456789') for _ in range(4)); os.makedirs(DASH, exist_ok=True)
    if not DRY:
        with open(DASH + '/pin', 'w') as f: f.write(new + '\n')
        os.chmod(DASH + '/pin', 0o600)
        try: json.dump({'seen': True, 'pin': new}, open(DASH + '/ack.json', 'w'))        # you are looking at it now: no "PIN changed" popup later
        except OSError: pass
    return True, 'New PIN: %s' % new

class Setting:
    def __init__(self, key, label, options, hint, get, set, only=None, free=False):
        # free=True: any valid value is accepted from the command line (the on-screen row only cycles through suggestions)
        self.key, self.label, self.options, self.hint, self.get, self.set, self.only, self.free = key, label, options, hint, get, set, only, free
    def shown(self, value): return dict(self.options).get(value, value)
    def next_value(self, cur):
        vals = [v for v, _ in self.options]
        return vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else vals[0]

SETTINGS = [
    Setting('boot', 'Start up in', [('console', 'Gaming Mode'), ('desktop', 'Desktop')],
            'Which mode the console starts in when you power it on. You can always switch from the menu.', get_boot, set_boot),
    Setting('display', 'Gaming Mode screen', [('720p', '720p (smoothest)'), ('1080p', '1080p'), ('native', 'Monitor’s best')],
            '720p is easiest on the Pi and is the default. Changes right now.', get_display, set_display, only='console'),
    Setting('startup_movie', 'Startup movie', [('steamed-pi', 'Steamed Pi'), ('none', 'Off'), ('steam', 'Steam’s own')],
            'The animation shown when Steam starts. Applies the next time Steam starts.', get_movie, set_movie),
    Setting('popups', 'Start-up notices', [('normal', 'When needed'), ('quiet', 'Problems only')],
            'The popup with the dashboard address and PIN. “Problems only” hides the welcome and new-PIN reminders.', get_popups, set_popups),
    Setting('safety', 'If Steam keeps failing', [('desktop', 'Switch to Desktop'), ('retry', 'Keep retrying')],
            'After repeated Steam failures the console can switch to the desktop so you are never stuck on a blank screen.', get_safety, set_safety),
    Setting('ssh', 'SSH', [('off', 'Off'), ('on', 'On')], 'Remote terminal access from your network. Stays on until you turn it off.', get_ssh, set_ssh),
    Setting('ftp', 'FTP (ROM transfer)', [('off', 'Off'), ('on', 'On')], 'Copy ROMs to the console over the network. Login details are in Console info.', get_ftp, set_ftp),
    Setting('iface', 'Address shown first', [('auto', 'Automatic'), ('wired', 'Ethernet'), ('wifi', 'Wi-Fi')],
            'Which network address the menu and dashboard list first when you use both Ethernet and Wi-Fi.', get_iface, set_iface),
    Setting('hostname', 'Console name', [('steamed-pi', 'steamed-pi'), ('steamed-pi-1', 'steamed-pi-1'), ('steamed-pi-2', 'steamed-pi-2'), ('living-room', 'living-room'), ('game-room', 'game-room'), ('tv', 'tv')],
            'The name this console has on your network (NAME.local). Cycle through suggestions here, or type any name in the dashboard.', get_hostname, set_hostname, free=True),
    Setting('look', 'Desktop look', [('steamed-pi', 'Steamed Pi'), ('ubuntu', 'Ubuntu default')],
            'Wallpaper, colors and terminal theme in Desktop mode. Takes a few seconds.', get_look, set_look),
    Setting('pin', 'New dashboard PIN', [], 'Press A to make a new PIN. Anyone using the dashboard from another device needs it.', get_pin, set_pin),
]
BY_KEY = {s.key: s for s in SETTINGS}
