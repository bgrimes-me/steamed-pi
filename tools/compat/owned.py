import struct, sys, json, os
def kv(b, i, strs=None):
    d = {}
    while True:
        t = b[i]; i += 1
        if t == 8: return d, i
        j = b.index(b'\0', i); k = b[i:j].decode('utf8', 'replace'); i = j + 1
        if t == 0: d[k], i = kv(b, i)
        elif t == 1: j = b.index(b'\0', i); d[k] = b[i:j].decode('utf8', 'replace'); i = j + 1
        elif t in (2, 4, 6): d[k] = struct.unpack_from('<i', b, i)[0]; i += 4
        elif t == 7: d[k] = struct.unpack_from('<Q', b, i)[0]; i += 8
        elif t == 3: d[k] = struct.unpack_from('<f', b, i)[0]; i += 4
        else: raise ValueError('type %d' % t)
b = open(os.path.join(os.environ.get('STEAM_DIR') or os.path.expanduser('~/.local/share/Steam'), 'appcache/packageinfo.vdf'), 'rb').read()
magic, uni = struct.unpack_from('<II', b, 0); i = 8; apps = set(); pk = 0
while True:
    pid = struct.unpack_from('<I', b, i)[0]; i += 4
    if pid == 0xFFFFFFFF: break
    i += 20 + 4 + 8
    if magic == 0x06565529: pass
    size = None
    d, i = kv(b, i)
    for v in d.values():
        if isinstance(v, dict) and 'appids' in v:
            for a in v['appids'].values(): apps.add(int(a))
    pk += 1
print(len(apps), 'apps in', pk, 'packages', file=sys.stderr)
json.dump(sorted(apps), open(sys.argv[1], 'w'))
