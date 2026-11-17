"""Rank the classified library and write two files into the work folder:
   library-compat.csv  every game with its verdict and the reason
   TEST-LIST.md        a readable list: what to download and test first
Run after classify.py (use run.sh)."""
import json, os, csv
from collections import Counter
WORK = os.environ.get('STEAMED_PI_COMPAT_DIR') or os.path.expanduser('~/.cache/steamed-pi/compat'); J = WORK + '/'
rows = json.load(open(J + 'classified.json')); app = json.load(open(J + 'appinfo.json'))
def score(x):
    s = (4 if x['frame'] == 3 else 2 if x['frame'] == 2 else 0) + (1 if x['deck'] == 3 else 0)
    s += (2 if (x['dx'] is not None and x['dx'] < 10) or x['gl_mention'] else 0) + (2 if x['two_d'] else 0)
    s += (1 if (x['year'] or 3000) <= 2014 else 0) + (1 if (x['ram_gb'] is not None and x['ram_gb'] <= 2) else 0)
    rv = app.get(x['appid'], {}).get('common', {}).get('review_percentage'); x['reviews'] = rv
    return s + (1 if rv and rv >= 90 else 0)
for x in rows: x['score'] = score(x)
order = {'Confirmed': 0, 'Try first': 1, 'Worth testing': 2, 'Unknown': 3, 'Unlikely': 4, 'Blocked (DXVK)': 5, 'No': 6}
rows.sort(key=lambda x: (order[x['tier']], -x['score'], x['name']))
RATING = {1: 'unsupported', 2: 'playable', 3: 'verified', None: ''}
with open(J + 'library-compat.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['appid', 'name', 'verdict', 'why', 'score', 'year', 'valve_arm_rating', 'valve_recommended_runtime', 'stated_directx', 'stated_opengl', 'stated_ram_gb', 'installed', 'tags'])
    for x in rows: w.writerow([x['appid'], x['name'], x['tier'], x['why'], x['score'], x['year'] or '', RATING[x['frame']], x['runtime'], x['dx'] or '', x['gl'] or '', x['ram_gb'] or '', 'yes' if x['installed'] else '', x['tags']])
cnt = Counter(x['tier'] for x in rows)
def table(rs, cols):
    s = '| ' + ' | '.join(c for c, _ in cols) + ' |\n|' + '---|' * len(cols) + '\n'
    for x in rs: s += '| ' + ' | '.join(str(f(x)) for _, f in cols) + ' |\n'
    return s
cols = [('Game', lambda x: x['name'].replace('|', '/')), ('Year', lambda x: x['year'] or ''), ('Why it should work', lambda x: x['why']), ('Valve ARM rating', lambda x: RATING[x['frame']] or '-')]
tf = [x for x in rows if x['tier'] == 'Try first' and not x['installed']]; wt = [x for x in rows if x['tier'] == 'Worth testing' and not x['installed']]
bl = sorted((x for x in rows if x['tier'] == 'Blocked (DXVK)'), key=lambda x: -(x['reviews'] or 0))
md = f"""# What should run on your Raspberry Pi 5

Built from the {len(rows)} games in your Steam library. Nothing here has been run: it is a **prediction** from data, to tell you what to download and test first.
Tell the tool which games you have confirmed working (one Steam app id per line in `confirmed.txt` in this folder) and it will show them as "Confirmed".

## Totals
{chr(10).join('- **%s**: %d' % (k, cnt[k]) for k in order if cnt[k])}

(`library-compat.csv` lists every game with its reason.)

## Try these first ({len(tf)} games, best candidates first)
{table(tf[:60], cols)}
## Then these ({len(wt)} games)
3D games or ones with an unstated graphics API: likely slow or fiddly, but not ruled out.

{table(wt[:40], cols)}
## Blocked by the DirectX 11/12 limit ({len(bl)} games)
Well-reviewed games that will not start until the Pi's graphics driver or DXVK changes.

{table(bl[:25], [('Game', lambda x: x['name'].replace('|', '/')), ('Year', lambda x: x['year'] or ''), ('Why', lambda x: x['why'][:60])])}
"""
open(J + 'TEST-LIST.md', 'w').write(md); print('wrote', J + 'TEST-LIST.md', 'and library-compat.csv;', dict(cnt))
