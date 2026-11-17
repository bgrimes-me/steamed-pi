#!/usr/bin/env python3
"""Steamed Pi dashboard: status, one-click SSH/FTP, reboot and friends.
Standard library + (optional) python3-pyftpdlib. Runs as the normal user; privileged actions use
`sudo -n` for a short allow-list of commands (see setup-root.sh)."""
import zlib, http.server, socketserver, json, os, sys, time, threading, subprocess, ipaddress, secrets, signal, shutil, socket, re

PORT = int(os.environ.get('DASH_PORT', '8080'))
HOME = os.path.expanduser('~')
CFG = os.path.join(HOME, '.config', 'steamed-pi', 'dashboard')
FTP_ROOT = os.path.join(HOME, 'ROMs')
FTP_USER = 'steamed-pi'
FTP_PORT = 2121 if os.environ.get('DASH_DEV') else 21
PASSIVE = (30000, 30009)
os.makedirs(CFG, exist_ok=True)
START = time.time()
LOCK = threading.Lock()
state = {'ftp': None, 'ssh_off_at': None}           # ftp: dict(user,password,off_at)
_ftp = {'server': None, 'thread': None}

def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def run(cmd, timeout=20):
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout); return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e: return 1, str(e)
def sudo(*cmd): return run(['sudo', '-n'] + list(cmd))

# ---------------- status helpers ----------------
def read(p, d=''):
    try: return open(p).read().strip()
    except OSError: return d
PREFS_FILE = os.path.join(CFG, 'prefs.json')
def prefs():
    try: p = json.load(open(PREFS_FILE))
    except (OSError, ValueError): p = {}
    return {'iface': p.get('iface', 'auto') if p.get('iface') in ('auto', 'wired', 'wifi') else 'auto'}
def kind(ifname): return 'wired' if ifname.startswith(('eth', 'en')) else 'wifi' if ifname.startswith(('wl',)) else 'other'
def ips():
    """Connected IPv4 addresses, the preferred adapter first. 'auto' = wired first, then Wi-Fi."""
    rc, out = run(['ip', '-4', '-o', 'addr', 'show', 'scope', 'global'])
    res = []
    for l in out.splitlines():
        p = l.split()
        if len(p) >= 4: res.append({'if': p[1], 'ip': p[3].split('/')[0], 'kind': kind(p[1])})
    want = {'auto': 'wired', 'wired': 'wired', 'wifi': 'wifi'}[prefs()['iface']]
    res.sort(key=lambda x: (x['kind'] != want, x['kind'] == 'other', x['if']))   # preferred kind first; falls back automatically
    return res
def mem():
    m = {}
    for l in read('/proc/meminfo').splitlines():
        k, v = l.split(':', 1); m[k] = int(v.split()[0]) // 1024
    used = m['MemTotal'] - m['MemAvailable']
    return {'total': m['MemTotal'], 'used': used, 'swap_used': m.get('SwapTotal', 0) - m.get('SwapFree', 0)}
def procs():
    out = []
    for pid in filter(str.isdigit, os.listdir('/proc')):
        try:
            if os.stat('/proc/%s' % pid).st_uid != os.getuid(): continue
            comm = read('/proc/%s/comm' % pid)
            out.append((int(pid), comm, read('/proc/%s/cmdline' % pid).replace('\0', ' ')))
        except OSError: pass
    return out
def _shortcut_ids():
    # Steam's id for the "Emulation" (ES-DE) non-Steam shortcut is derived from its command and name: compute it, don't hardcode it
    exe = os.path.join(HOME, '.local', 'bin', 'es-de-launch'); aid = zlib.crc32(('"%s"Emulation' % exe).encode()) | 0x80000000
    return str(aid), str((aid << 32) | 0x02000000)
ESDE_IDS = _shortcut_ids()
EMULATORS = ('retroarch', 'dolphin-emu', 'ppsspp', 'PPSSPPSDL', 'duckstation', 'flycast', 'mupen64plus', 'pcsx2')
def console_status():
    P = procs(); names = [c for _, c, _ in P]
    steam = 'steam' in names
    games = []
    for pid, comm, cmd in P:
        if comm in EMULATORS: games.append(comm)
        m = re.search(r'reaper SteamLaunch AppId=(\d+)', cmd)
        if m and 'es-de-launch' not in cmd and int(m.group(1)) < 2**31: games.append('Steam game ' + m.group(1))
    pads = [l.split('Name=')[1].strip('"') for l in read('/proc/bus/input/devices').splitlines() if l.startswith('N: Name=') and re.search(r'8BitDo|X-Box|Xbox|Gamepad|Controller', l, re.I) and 'Steam' not in l and 'keyboard' not in l.lower() and 'virtual' not in l.lower() or 'X-Box' in l and l.startswith('N: Name=')]
    return {'steam': steam, 'webhelpers': names.count('steamwebhelper'), 'esde': 'es-de' in names, 'games': sorted(set(games)),
            'controllers': pads[:3]}
def svc_active(unit, user=False):
    rc, out = run(['systemctl'] + (['--user'] if user else []) + ['is-active', unit]); return out.strip() == 'active'
def ssh_units():
    rc, out = run(['systemctl', 'list-unit-files', 'ssh.socket', 'ssh.service', '--no-legend'])
    return [l.split()[0] for l in out.splitlines() if l.strip()]
def ssh_state():
    u = ssh_units()
    if not u: return {'installed': False, 'on': False}
    on = any(svc_active(x) for x in u)
    return {'installed': True, 'on': on, 'port': 22, 'off_at': state['ssh_off_at'] if on else None}
def ftp_state():
    try: import pyftpdlib  # noqa
    except ImportError: return {'installed': False, 'on': False}
    f = state['ftp']
    return {'installed': True, 'on': bool(f), 'user': FTP_USER if f else None, 'password': f['password'] if f else None,
            'off_at': f['off_at'] if f else None, 'port': FTP_PORT}
def status():
    t = read('/sys/class/thermal/thermal_zone0/temp')
    du = shutil.disk_usage('/')
    return {'host': socket.gethostname(), 'user': os.environ.get('USER') or os.path.basename(HOME), 'ips': ips(), 'uptime': int(float(read('/proc/uptime').split()[0])),
            'temp': round(int(t) / 1000, 1) if t else None, 'load': read('/proc/loadavg').split()[:3], 'mem': mem(),
            'disk': {'total': du.total // 2**30, 'used': (du.total - du.free) // 2**30},
            'prefer': prefs()['iface'], 'mode': 'console' if any(c == 'labwc' for _, c, _ in procs()) else 'desktop', 'console': console_status(), 'home_service': svc_active('steamed-pi-controller-home.service', True),
            'ssh': ssh_state(), 'ftp': ftp_state(), 'now': int(time.time()), 'pin_required': os.path.exists(os.path.join(CFG, 'pin')),
            'sudo_ok': sudo('-l', '/usr/bin/systemctl', 'reboot')[0] == 0}

# ---------------- SSH ----------------
def ssh_set(on, minutes=0):
    units = ssh_units()
    if not units: return False, 'OpenSSH server is not installed yet (run setup-root.sh)'
    sock = [u for u in units if u.endswith('.socket')]
    if on:
        rc, out = sudo('systemctl', 'start', sock[0] if sock else 'ssh.service')
        state['ssh_off_at'] = int(time.time() + minutes * 60) if minutes else None
    else:
        rc, out = 0, ''
        for u in units: rc2, o = sudo('systemctl', 'stop', u); rc, out = (rc2 or rc), (out + o)
        state['ssh_off_at'] = None
    save_state()
    return rc == 0, out or ('SSH enabled' if on else 'SSH disabled')

# ---------------- FTP ----------------
def ftp_set(on, minutes=0):
    with LOCK:
        if on:
            if state['ftp']: return True, 'FTP already on'
            try:
                from pyftpdlib.authorizers import DummyAuthorizer
                from pyftpdlib.handlers import FTPHandler
                from pyftpdlib.servers import FTPServer
            except ImportError: return False, 'python3-pyftpdlib is not installed yet (run setup-root.sh)'
            os.makedirs(FTP_ROOT, exist_ok=True)
            pw = ''.join(secrets.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(8))
            auth = DummyAuthorizer(); auth.add_user(FTP_USER, pw, FTP_ROOT, perm='elradfmwMT')
            class H(FTPHandler): pass
            H.authorizer = auth; H.passive_ports = range(PASSIVE[0], PASSIVE[1] + 1); H.banner = 'Steamed Pi ROM share'
            try: srv = FTPServer(('0.0.0.0', FTP_PORT), H)
            except OSError as e: return False, 'cannot listen on port %d: %s' % (FTP_PORT, e)
            th = threading.Thread(target=srv.serve_forever, kwargs={'handle_exit': False}, daemon=True); th.start()
            _ftp['server'], _ftp['thread'] = srv, th
            state['ftp'] = {'password': pw, 'off_at': int(time.time() + minutes * 60) if minutes else None}
            log('FTP on'); return True, 'FTP enabled'
        else:
            srv = _ftp['server']
            if srv:
                try: srv.close_all()
                except Exception as e: log('ftp close:', e)
            _ftp['server'] = _ftp['thread'] = None; state['ftp'] = None; log('FTP off'); return True, 'FTP disabled'

def save_state():
    try: json.dump({'ssh_off_at': state['ssh_off_at']}, open(os.path.join(CFG, 'state.json'), 'w'))
    except OSError: pass
def watchdog():
    while True:
        time.sleep(15); now = time.time()
        f = state['ftp']
        if f and f['off_at'] and now >= f['off_at']: ftp_set(False)
        if state['ssh_off_at'] and now >= state['ssh_off_at'] and ssh_state().get('on'): ssh_set(False)

# ---------------- other actions ----------------
def later(fn, delay=1.0): threading.Timer(delay, fn).start()
def close_game():
    n = 0
    for pid, comm, cmd in procs():
        if comm in EMULATORS or (re.search(r'reaper SteamLaunch AppId=\d+', cmd) and 'es-de-launch' not in cmd and ('AppId=' + ESDE_IDS[0]) not in cmd and ('AppId=' + ESDE_IDS[1]) not in cmd):
            try: os.kill(pid, signal.SIGTERM); n += 1
            except OSError: pass
    return n > 0, ('Asked %d process(es) to close' % n) if n else 'No game or emulator is running'
def restart_steam():
    s = os.path.join(HOME, '.local', 'bin', 'steamed-pi-restart-steam')
    subprocess.Popen([s], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, 'Restarting Steam...'
def action(name, params):
    mins = int(params.get('minutes', 0) or 0)
    if name == 'set_hostname':
        helper = '/usr/local/sbin/steamed-pi-set-hostname'
        new = str(params.get('value', '')).strip().lower()
        if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', new): return False, 'Use 1-63 letters, digits and hyphens, not starting or ending with a hyphen'
        if not os.path.exists(helper): return False, 'The renaming helper is not installed yet: run ./install.sh again (it installs it)'
        if new == socket.gethostname(): return True, 'The name is already %s' % new
        rc, out = sudo(helper, new)
        if rc != 0: return False, (out or 'could not change the name')[-160:]
        try: os.makedirs(CFG, exist_ok=True); open(os.path.join(os.path.dirname(CFG), 'hostname-chosen'), 'w').close()
        except OSError: pass
        later(lambda: None); return True, 'Name changed to %s. Reach this console at %s.local (reload this page at the new address).' % (new, new)
    if name == 'set_iface':
        v = params.get('value')
        if v not in ('auto', 'wired', 'wifi'): return False, 'bad value'
        json.dump({'iface': v}, open(PREFS_FILE, 'w')); return True, 'Showing the %s address first' % {'auto': 'wired (auto)', 'wired': 'wired', 'wifi': 'Wi-Fi'}[v]
    if name in ('switch_desktop', 'switch_console'):
        subprocess.Popen([os.path.join(HOME, '.local', 'bin', 'steamed-pi-session-switch'), name.split('_')[1]], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, 'Switching to %s mode...' % name.split('_')[1]
    if name == 'ssh_on': return ssh_set(True, mins)
    if name == 'ssh_off': return ssh_set(False)
    if name == 'ftp_on': return ftp_set(True, mins)
    if name == 'ftp_off': return ftp_set(False)
    if name == 'close_game': return close_game()
    if name == 'restart_steam': return restart_steam()
    if name == 'restart_home_service': return (run(['systemctl', '--user', 'restart', 'steamed-pi-controller-home.service'])[0] == 0, 'Home-button service restarted')
    if name == 'reboot': later(lambda: sudo('systemctl', 'reboot')); return True, 'Rebooting...'
    if name == 'poweroff': later(lambda: sudo('systemctl', 'poweroff')); return True, 'Powering off...'
    return False, 'unknown action'

# ---------------- HTTP ----------------
def client_ok(ip):
    try: a = ipaddress.ip_address(ip.split('%')[0])
    except ValueError: return False
    if a.version == 6 and a.ipv4_mapped: a = a.ipv4_mapped
    return a.is_private or a.is_loopback or a.is_link_local

class H(http.server.BaseHTTPRequestHandler):
    server_version = 'SteamedPiDash'
    def log_message(self, f, *a): pass
    def _send(self, code, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header('Content-Type', ctype if ctype.startswith('image/') else ctype + '; charset=utf-8'); self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Frame-Options', 'DENY'); self.end_headers(); self.wfile.write(b)
    def _guard(self):
        if not client_ok(self.client_address[0]): self._send(403, '{"error":"LAN only"}'); return False
        return True
    def do_GET(self):
        if not self._guard(): return
        if self.path in ('/', '/index.html'): return self._send(200, PAGE, 'text/html')
        if self.path in ('/brand/logo.png', '/brand/icon.png'):
            b = brand_logo(os.path.basename(self.path))
            return self._send(200, b, 'image/png') if b else self._send(404, '{"error":"no logo"}')
        if self.path == '/api/status': return self._send(200, json.dumps(status()))
        self._send(404, '{"error":"not found"}')
    def do_POST(self):
        if not self._guard(): return
        # CSRF: must be a same-origin fetch() carrying our custom header
        if self.headers.get('X-Dashboard') != '1': return self._send(403, '{"error":"bad request"}')
        org = self.headers.get('Origin')
        if org and re.sub(r'^https?://', '', org) != self.headers.get('Host'): return self._send(403, '{"error":"cross-origin"}')
        pinf = os.path.join(CFG, 'pin')
        if os.path.exists(pinf) and not secrets.compare_digest(self.headers.get('X-Pin', ''), read(pinf)): return self._send(401, '{"error":"PIN required","pin":true}')
        n = int(self.headers.get('Content-Length') or 0)
        try: body = json.loads(self.rfile.read(n) or b'{}')
        except ValueError: return self._send(400, '{"error":"bad json"}')
        if self.path != '/api/action': return self._send(404, '{"error":"not found"}')
        ok, msg = action(body.get('name', ''), body); log('action', body.get('name'), '->', ok, msg[:80])
        self._send(200, json.dumps({'ok': ok, 'message': msg}))

class Srv(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True
    address_family = socket.AF_INET6
    def server_bind(self):
        try: self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except OSError: pass
        super().server_bind()

sys.path.insert(0, os.path.expanduser('~/.local/lib/steamed-pi'))
try: import steamed_pi_palette
except ImportError: steamed_pi_palette = None
def build_page():
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')).read()
    if not steamed_pi_palette: return html
    c = steamed_pi_palette.load()
    css = ':root{--bg:%(BG_DESKTOP)s;--card:%(CARD)s;--line:%(LINE)s;--text:%(TEXT)s;--mute:%(MUTED)s;--accent:%(ACCENT)s;--on-accent:%(ON_ACCENT)s;--ok:%(OK)s;--warn:%(WARN)s;--bad:%(BAD)s}' % c
    return html.replace('</head>', '<style id="palette">%s</style></head>' % css, 1)
PAGE = build_page()
def brand_logo(name='logo.png'):
    f = steamed_pi_palette.load().get('BRAND_LOGO') if steamed_pi_palette else None      # logo.png and icon.png live in the same folder
    if f and name != 'logo.png': f = os.path.join(os.path.dirname(f), name)
    try: return open(f, 'rb').read() if f else None
    except OSError: return None
if __name__ == '__main__':
    try:
        d = json.load(open(os.path.join(CFG, 'state.json'))); state['ssh_off_at'] = d.get('ssh_off_at')
    except (OSError, ValueError): pass
    # Fresh random PIN on every start when ~/.config/steamed-pi/dashboard/pin-auto exists (the installer creates it; the Home menu
    # shows the PIN). Delete pin-auto and put your own digits in the 'pin' file to choose a fixed PIN instead.
    pinf, gen = os.path.join(CFG, 'pin'), os.path.join(CFG, 'pin.generated')
    if os.path.exists(os.path.join(CFG, 'pin-auto')):
        pin = '%04d' % secrets.randbelow(10000)
        fd = os.open(pinf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.write(fd, pin.encode()); os.close(fd)
        open(gen, 'w').close(); log('dashboard PIN for this run: %s (file: %s)' % (pin, pinf))
    elif os.path.exists(gen):
        for f in (pinf, gen):
            try: os.remove(f)
            except OSError: pass
    threading.Thread(target=watchdog, daemon=True).start()
    try: httpd = Srv(('::', PORT), H)
    except OSError:
        Srv.address_family = socket.AF_INET; httpd = Srv(('0.0.0.0', PORT), H)
    log('dashboard listening on', PORT)
    signal.signal(signal.SIGTERM, lambda *a: (ftp_set(False), os._exit(0)))
    httpd.serve_forever()
