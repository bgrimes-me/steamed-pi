Steamed Pi brand marks
======================

logo-compact/   "btgprojects presents" + steamed pi + steaming cursor, condensed for use inline with a title.
                The presents line is justified to the exact width of "steamed" and tucked under the steam's headroom.
                The steam is the wallpaper's steam cloud (same maths as render.py), scaled to the cursor.
  steamed-pi-compact-dark-bg.svg / -{200,400,800,1600,3200}w.png    for dark UIs
  steamed-pi-compact-light-bg.svg / -{...}w.png                     for light UIs (near-black text, grey steam)

icon/           "sp" + steaming cursor on a black rounded tile, no glow. Same steam cloud.
                The cursor spans the x-height: its top lines up with the tops of s and p, its bottom with
                the baseline, so only the p's leg dips below. 16 and 32 are hand-tuned pixel grids.
  steamed-pi-icon.svg, steamed-pi-icon.ico (16/32/48), steamed-pi-icon-{16..1024}.png

All text is converted to outlines, so the SVGs render the same without Tektur / JetBrains Mono installed.
brand.py regenerates everything (needs rsvg-convert and fonttools).
