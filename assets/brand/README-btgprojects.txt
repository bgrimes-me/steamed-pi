btgprojects.dev icons
=====================

favicon/   "b + cursor" mark: Tektur 700 'b' in #f2ede4 + #ffc53d cursor on a #000 rounded tile.
           The cursor matches the b's height (top of the b to the baseline) and keeps the site
           cursor's 0.5 : 0.92 proportions.
  favicon.svg                     modern browsers (pixel-snapped 16-grid, crisp at tab sizes)
  favicon.ico                     16/32/48 legacy
  favicon-{size}.png              16, 32, 48, 64, 96, 128, 192, 256, 512, 1024 (tiled)
  favicon-{size}-transparent.png  same mark with no tile (for dark surfaces only)
  apple-touch-icon.png            180x180
  logo-mark.svg / logo-mark-transparent.svg   exact unsnapped vector master from the font outline

cursor/    cursor-only icon: #ffc53d block (0.5em x 0.92em proportions) with soft drop shadow
           and a faint gold glow, transparent background
  cursor.svg, cursor.ico, cursor-{size}.png (16 to 1024)

logo/      the b + cursor mark (cursor = b height) with the same drop shadow as the cursor icon,
           plus a faint gold glow behind the cursor; transparent background, no tile
  btgprojects-logo.svg
  btgprojects-logo-{width}w.png   128, 256, 512, 1024, 2048, 4096 px wide

make_icons.py   regenerates everything (needs rsvg-convert)

Suggested <head> tags (replace the current favicon links in source/src/shell.mjs):

  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">

Web app manifest icons:

  "icons": [
    { "src": "/favicon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/favicon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
