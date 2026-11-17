import struct, os, json, sys
b = open(os.path.join(os.environ.get('STEAM_DIR') or os.path.expanduser('~/.local/share/Steam'), 'appcache/appinfo.vdf'), 'rb').read()
magic, uni = struct.unpack_from('<II', b, 0); sto = struct.unpack_from('<q', b, 8)[0]
n = struct.unpack_from('<I', b, sto)[0]; i = sto + 4; strs = []
for _ in range(n):
    j = b.index(b'\0', i); strs.append(b[i:j].decode('utf8', 'replace')); i = j + 1
def kv(i, end):
    d = {}
    while i < end:
        t = b[i]; i += 1
        if t == 8: return d, i
        k = strs[struct.unpack_from('<I', b, i)[0]]; i += 4
        if t == 0: d[k], i = kv(i, end)
        elif t == 1: j = b.index(b'\0', i); d[k] = b[i:j].decode('utf8', 'replace'); i = j + 1
        elif t in (2, 4, 6): d[k] = struct.unpack_from('<i', b, i)[0]; i += 4
        elif t == 7: d[k] = struct.unpack_from('<Q', b, i)[0]; i += 8
        elif t == 3: d[k] = struct.unpack_from('<f', b, i)[0]; i += 4
        else: raise ValueError(t)
    return d, i
i = 16; apps = {}
while i < sto:
    appid, size = struct.unpack_from('<II', b, i)
    if appid == 0: break
    body = i + 8; end = body + size
    try:
        d, _ = kv(body + 60, end)
        apps[appid] = d.get('appinfo', d)
    except Exception as e: pass
    i = end
json.dump(apps, open(sys.argv[1], 'w'))
print(len(apps), 'apps parsed; magic', hex(magic), file=sys.stderr)
