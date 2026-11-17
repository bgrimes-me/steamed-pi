#!/bin/bash
# Make a custom Steam startup movie from a still image and install it as an override.
#   usage:  make-startup-movie.sh logo.png [seconds=4] [--test]
# - builds a small 1280x720 VP9 WebM (letterboxed on black) with GStreamer; a static image compresses to a few KB
#   and decodes cheaply, so the startup never stutters
# - installs it under every startup-movie name Steam may use, in ~/.local/share/Steam/config/uioverrides/movies/
#   (outside Steam's own files, so Steam updates don't touch it).  Undo:  rm -r ~/.local/share/Steam/config/uioverrides/movies
# - --test writes to /tmp only and does not install anything
set -euo pipefail
IN=${1:?usage: make-startup-movie.sh image.png [seconds] [--test]}; SECS=${2:-4}; MODE=${3:-}
FPS=15; FR=$((FPS * SECS))
case "${IN,,}" in *.png) DEC=pngdec;; *.jpg|*.jpeg) DEC=jpegdec;; *.webm) DEC="";; *) echo "Give me a .png/.jpg still image or a ready-made .webm (I can't decode H.264 video on this machine)."; exit 1;; esac
OUT=$(mktemp -d)/startup.webm
if [ -z "$DEC" ]; then cp "$IN" "$OUT"; else
gst-launch-1.0 -q -e filesrc location="$IN" ! $DEC ! videoconvert ! imagefreeze num-buffers=$FR ! videoscale add-borders=true \
  ! "video/x-raw,width=1280,height=720,pixel-aspect-ratio=1/1,framerate=$FPS/1" ! videoconvert ! \
  vp9enc deadline=1 cpu-used=5 target-bitrate=600000 min-quantizer=10 max-quantizer=40 keyframe-max-dist=$FPS ! webmmux ! filesink location="$OUT"
fi
echo "built $OUT: $(stat -c %s "$OUT") bytes, ${SECS}s, ${FPS} fps"
# verify it decodes
gst-launch-1.0 -q filesrc location="$OUT" ! matroskademux ! vp9dec ! fakesink && echo "decode check: ok"
[ "$MODE" = "--test" ] && { echo "(test mode: nothing installed)  file: $OUT"; exit 0; }
# keep a master copy outside Steam's folders, so the override can always be rebuilt
M=$HOME/.local/share/steamed-pi/art/startup; mkdir -p "$M"; cp "$OUT" "$M/startup.webm"
D=$HOME/.local/share/Steam/config/uioverrides/movies; mkdir -p "$D"
for n in steam_os_startup bigpicture_startup steam_os_family_startup startup_machine deck_startup oled_startup steamframe_startup_450x450; do cp "$OUT" "$D/$n.webm"; done
echo "installed as $(ls "$D" | wc -l) overrides in $D"; echo "Restart Steam to see it."
