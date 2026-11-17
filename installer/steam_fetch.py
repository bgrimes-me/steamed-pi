#!/usr/bin/python3 -I
"""Download Valve's native ARM64 Steam client bootstrap package and unpack it.
Valve's software is fetched from Valve's own servers at install time and is never stored in this repository.

    steam_fetch.py DEST_DIR [--force]

Finds the package in Valve's public manifest, checks its size and SHA-256 against the manifest, then extracts it
(the zip uses backslash path separators and does not mark programs executable, so both are fixed up here)."""
import re, sys, os, hashlib, urllib.request, zipfile, tempfile, shutil
BASE = 'https://client-update.steamstatic.com/'
MANIFEST = 'steam_client_linuxarm64'
PACKAGE = 'bins_linuxarm64_linuxarm64'
UA = {'User-Agent': 'steamed-pi-installer'}

def get(url, timeout=120): return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args: sys.exit(__doc__)
    dest = os.path.abspath(args[0]); force = '--force' in sys.argv
    marker = os.path.join(dest, 'steamrtarm64', 'steam')
    if os.path.isfile(marker) and not force:
        print('already installed: %s (use --force to download again)' % marker); return 0
    print('reading the manifest...')
    text = get(BASE + MANIFEST).read().decode('utf-8', 'replace')
    block = re.search(r'"%s"\s*\{(.*?)\}' % PACKAGE, text, re.S)
    if not block: sys.exit('package %s is not in the manifest (Valve changed the layout?)' % PACKAGE)
    field = lambda k: re.search(r'"%s"\s+"([^"]+)"' % k, block.group(1)).group(1)
    name, size, sha = field('file'), int(field('size')), field('sha2')
    print('downloading %s (%.0f MB)...' % (PACKAGE, size / 1e6))
    os.makedirs(dest, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        zpath = os.path.join(tmp, 'pkg.zip'); h = hashlib.sha256(); got = 0
        with get(BASE + name, timeout=300) as r, open(zpath, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                f.write(chunk); h.update(chunk); got += len(chunk)
        if got != size or h.hexdigest() != sha:
            sys.exit('download check FAILED (got %d bytes, sha256 %s...): not installing it' % (got, h.hexdigest()[:12]))
        print('download verified (size and SHA-256 match Valve\'s manifest)')
        z = zipfile.ZipFile(zpath)
        for info in z.infolist():
            rel = info.filename.replace('\\', '/').lstrip('/')
            if '..' in rel.split('/'): sys.exit('refusing unsafe path in package: ' + rel)
            out = os.path.join(dest, rel)
            if info.is_dir() or rel.endswith('/'): os.makedirs(out, exist_ok=True); continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(info) as src, open(out, 'wb') as dst: shutil.copyfileobj(src, dst)
            with open(out, 'rb') as f: magic = f.read(4)
            if magic == b'\x7fELF' or rel.endswith('.sh'): os.chmod(out, 0o755)     # programs and libraries
            else: os.chmod(out, 0o644)
    if not os.path.isfile(marker): sys.exit('unpacked, but %s is missing' % marker)
    print('installed Valve\'s ARM64 Steam client into', dest); return 0

if __name__ == '__main__': sys.exit(main())
