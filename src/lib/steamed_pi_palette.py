"""Reads the shared Steamed Pi palette (theme/palette.conf). Falls back to built-in defaults, so UI code never breaks."""
import os, re
DEFAULTS = dict(ACCENT='#FFC53D', TEXT='#F2EDE4', MUTED='#847D74', TAN='#E2B276', COPPER='#B07642', SPARK='#C8691F',
                BG_DESKTOP='#040404', BG_TERMINAL='#0D0A07', CARD='#17110C', LINE='#3A2416', FOCUS_BG='#2A1A0C',
                OK='#8FB85A', BAD='#E5533D', WARN='#C8691F', ON_ACCENT='#0D0A07')
CANDIDATES = [os.path.expanduser('~/.local/share/steamed-pi/theme/palette.conf'), os.path.expanduser('~/.config/steamed-pi/palette.conf')]
def load():
    p = dict(DEFAULTS)
    for f in CANDIDATES:
        try: text = open(f).read()
        except OSError: continue
        for m in re.finditer(r'^([A-Z_]+)="([^"]*)"', text, re.M):
            k, v = m.group(1), os.path.expandvars(m.group(2))
            if k in p or k == 'BRAND_LOGO': p[k] = v
        break
    return p
