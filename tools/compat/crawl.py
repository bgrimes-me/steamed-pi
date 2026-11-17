import json, os, time, urllib.request, urllib.error, sys
WORK = os.environ.get('STEAMED_PI_COMPAT_DIR') or os.path.expanduser('~/.cache/steamed-pi/compat'); os.makedirs(WORK, exist_ok=True)
STEAM = os.environ.get('STEAM_DIR') or os.path.expanduser('~/.local/share/Steam')
J = WORK + '/'; D = J + 'store/'; os.makedirs(D, exist_ok=True)
a = json.load(open(J + 'appinfo.json')); own = set(map(str, json.load(open(J + 'owned_apps.json'))))
ids = sorted(k for k, v in a.items() if k in own and str(v.get('common', {}).get('type', '')).lower() == 'game')
print(len(ids), 'games to fetch', flush=True)
UA = 'steamed-pi-compat'; wait = 1.6
for n, k in enumerate(ids):
    f = D + k + '.json'
    if os.path.exists(f): continue
    url = 'https://store.steampowered.com/api/appdetails?appids=%s&cc=us&l=english&filters=basic,platforms,categories,release_date' % k
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30).read()
            open(f, 'wb').write(r); break
        except urllib.error.HTTPError as e:
            if e.code in (429, 403): print('rate limited, sleeping 90 s', flush=True); time.sleep(90)
            else: open(f, 'w').write('{}'); break
        except Exception as e: time.sleep(10)
    if n % 50 == 0: print(n, 'done', flush=True)
    time.sleep(wait)
print('finished', flush=True)
