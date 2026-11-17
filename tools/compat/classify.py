import json, re, os, glob, csv, sys
WORK = os.environ.get('STEAMED_PI_COMPAT_DIR') or os.path.expanduser('~/.cache/steamed-pi/compat'); os.makedirs(WORK, exist_ok=True)
STEAM = os.environ.get('STEAM_DIR') or os.path.expanduser('~/.local/share/Steam')
J = WORK + '/'
a = json.load(open(J + 'appinfo.json')); own = set(map(str, json.load(open(J + 'owned_apps.json'))))
tags = {t['tagid']: t['name'] for t in json.load(open(J + 'tags.json'))['response']['tags']}
installed = {re.search(r'appmanifest_(\d+)', f).group(1) for f in glob.glob(os.path.join(STEAM, 'steamapps/appmanifest_*.acf'))}
# games the user has CONFIRMED working on this Pi (needs Proton ARM + launch options)
CONFIRMED = {}       # games YOU have confirmed work on your Pi: one Steam app id per line in WORK/confirmed.txt (optional)
try: CONFIRMED = {l.split()[0]: l.strip() for l in open(J + 'confirmed.txt') if l.strip() and not l.startswith('#')}
except OSError: pass
strip = lambda h: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h or '')).strip()
def req_text(x):
    pr = x.get('pc_requirements')
    if isinstance(pr, dict): return strip(pr.get('minimum', ''))
    return ''
def parse(txt):
    t = txt; r = {}
    m = re.findall(r'direct\s*x[^0-9]{0,40}?(\d+(?:\.\d+)?)', t, re.I) or re.findall(r'dx\s*(\d+)', t, re.I)
    r['dx'] = max(float(v) for v in m) if m else None
    m = re.findall(r'opengl[^0-9]{0,20}?(\d(?:\.\d)?)', t, re.I); r['gl'] = max(float(v) for v in m) if m else None
    r['gl_mention'] = bool(re.search(r'opengl', t, re.I)); r['vulkan'] = bool(re.search(r'vulkan', t, re.I))
    m = re.search(r'(?:memory|ram)[^0-9]{0,15}(\d+(?:\.\d+)?)\s*(gb|mb)', t, re.I)
    r['ram_gb'] = (float(m.group(1)) / (1024 if m.group(2).lower() == 'mb' else 1)) if m else None
    r['gpu_modern'] = bool(re.search(r'\b(rtx|gtx\s?(9\d\d|10\d\d|16\d\d|7[5-9]\d)|rx\s?\d{3}|radeon\s+(rx|vega|r[79]\s?\d{3})|arc\s?a\d)', t, re.I))
    r['gpu_heavy'] = r['gpu_modern'] or bool(re.search(r'\b(gtx|radeon\s+(hd\s?[5-9]\d{3}|r[579])|geforce\s+(gtx|[6-9]\d\d))', t, re.I))
    r['dx12'] = bool(re.search(r'direct\s*x[^0-9]{0,20}12|dx\s*12|directx 12', t, re.I))
    return r
H3D = ('3D', 'First-Person', 'Third Person', 'Open World', 'FPS', 'Third-Person Shooter', '3D Platformer', 'Flight', 'Walking Simulator', 'Realistic', 'Racing', '3D Fighter', 'Driving', 'Survival Horror', 'Immersive Sim', 'Souls-like')
rows = []
for k, v in a.items():
    if k not in own: continue
    c = v.get('common', {})
    if str(c.get('type', '')).lower() != 'game': continue
    f = J + 'store/' + k + '.json'
    s = {}
    if os.path.exists(f):
        try:
            d = json.load(open(f)); s = (d.get(k) or {}).get('data') or {}
        except Exception: s = {}
    fr = c.get('steam_frame_compatibility', {}); dk = c.get('steam_deck_compatibility', {})
    tg = [tags.get(int(t), '') for t in (c.get('store_tags') or {}).values()]
    cats = {x['id'] for x in s.get('categories', [])} if s else set()
    catnames = ' '.join(x['description'] for x in s.get('categories', [])) if s else ''
    txt = req_text(s) if s else ''; p = parse(txt) if txt else {}
    year = None
    m = re.search(r'(\d{4})', (s.get('release_date') or {}).get('date', '')) if s else None
    if m: year = int(m.group(1))
    elif c.get('steam_release_date'): year = 1970 + int(c['steam_release_date']) // 31556952
    rows.append(dict(appid=k, name=c.get('name', ''), year=year, installed=k in installed, confirmed=k in CONFIRMED,
        frame=fr.get('category'), runtime=fr.get('configuration', {}).get('recommended_runtime', ''), deck=dk.get('category'),
        windows=(s.get('platforms', {}).get('windows') if s else None), linux=(s.get('platforms', {}).get('linux') if s else None),
        has_req=bool(txt), dx=p.get('dx'), dx12=p.get('dx12'), gl=p.get('gl'), gl_mention=p.get('gl_mention'), vulkan=p.get('vulkan'),
        ram_gb=p.get('ram_gb'), gpu_heavy=p.get('gpu_heavy'), gpu_modern=p.get('gpu_modern'), single=(2 in cats) if cats else None, multi_only=bool(cats) and 2 not in cats,
        vac=8 in cats, pvp=36 in cats or 49 in cats, vr=bool(re.search(r'\bVR\b', catnames)) and 'VR Supported' not in catnames or 'VR Only' in tg,
        tags=';'.join(t for t in tg if t)[:140], two_d=(any(t in tg for t in ('2D', 'Pixel Graphics', 'Retro', '2D Platformer', 'Text-Based', 'Visual Novel', 'Card Game', 'Side Scroller', 'Metroidvania', 'Platformer', 'Arcade', 'Top-Down', 'Roguelite', 'Puzzle-Platformer', 'Point & Click', 'Card Battler', 'Deckbuilding', 'Hack and Slash', 'Beat em up', 'Shoot \'Em Up', 'Bullet Hell', 'Fighting', 'Rhythm', 'Tower Defense', 'Board Game', 'Match 3')) and not any(t in tg for t in H3D)), h3d=any(t in tg for t in H3D)))
def tier(r):
    """Decide how likely a game is to run on a Pi 5 under Proton ARM64 (FEX) with V3DV (no DXVK)."""
    if r['confirmed']: return 'Confirmed', 'you confirmed it works'
    if r['vr']: return 'No', 'VR title'
    if r['frame'] == 1: return 'No', 'Valve rates it unsupported on ARM'
    if r['multi_only'] or r['vac']: return 'No', 'online-only / anti-cheat'
    if r['gpu_modern'] or (r['gpu_heavy'] and (r['year'] or 0) >= 2014) or (r['ram_gb'] or 0) >= 8: return 'No', 'asks for a gaming GPU / 8 GB+'
    dx = r['dx']; heavy_api = (dx is not None and dx >= 11) or r['dx12'] or (r['gl'] is not None and r['gl'] >= 4)
    if heavy_api: return 'Blocked (DXVK)', ('needs DirectX %s: DXVK needs a GPU feature the Pi lacks' % (int(dx) if dx else 12)) if (dx or r['dx12']) else ('needs OpenGL %g: the Pi offers 3.1' % r['gl'])
    light = r['two_d'] or (not r['h3d'] and ((r['year'] or 3000) <= 2013 or (r['ram_gb'] is not None and r['ram_gb'] <= 2)))
    oldish = (r['year'] or 3000) <= 2013
    if dx is not None and dx < 11: api = 'DirectX %g' % dx
    elif r['gl'] is not None and r['gl'] <= 3.4: api = 'OpenGL %g' % r['gl']
    elif r['gl_mention']: api = 'OpenGL'
    else: api = 'API not stated'
    good_api = api != 'API not stated'
    if r['frame'] == 3 and light: return 'Try first', 'Valve ARM-verified; %s%s' % (api, '; light' if light else '')
    if good_api and light: return 'Try first', '%s; light/2D/older' % api
    if r['frame'] == 3 and good_api: return 'Worth testing', 'Valve ARM-verified, but 3D; %s' % api
    if r['frame'] == 2 and light: return 'Worth testing', 'Valve ARM-playable; %s; light' % api
    if good_api and r['h3d'] and (oldish or r['frame'] in (2, 3)): return 'Worth testing', '3D, %s: may be slow' % api
    if good_api: return 'Worth testing', api
    if light and r['has_req']: return 'Worth testing', 'light/2D/older (API unstated)'
    if not r['has_req']: return 'Unknown', 'no store data (not yet fetched, or none)'
    return 'Unlikely', 'API unstated and not clearly light'
for r in rows: r['tier'], r['why'] = tier(r)
json.dump(rows, open(J + 'classified.json', 'w'))
from collections import Counter
print(len(rows), Counter(r['tier'] for r in rows))
