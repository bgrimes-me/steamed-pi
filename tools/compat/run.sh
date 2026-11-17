#!/bin/bash
# Predict which games in YOUR Steam library should run on the Pi 5. Steam must have run (and been signed in) at least once.
#   tools/compat/run.sh            fetch store data (about 2 seconds per game: ~35 minutes for 1,000 games) and write the report
#   tools/compat/run.sh --quick    skip the store fetch if it was done before (re-rank only)
# Output: ~/.cache/steamed-pi/compat/TEST-LIST.md and library-compat.csv   (set STEAMED_PI_COMPAT_DIR to change the folder)
# Privacy: it asks Valve's public store API about the app ids in your library, one per request, and nothing else.
set -euo pipefail
HERE=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
export STEAMED_PI_COMPAT_DIR=${STEAMED_PI_COMPAT_DIR:-$HOME/.cache/steamed-pi/compat}; mkdir -p "$STEAMED_PI_COMPAT_DIR"; W=$STEAMED_PI_COMPAT_DIR
python3 -I "$HERE/owned.py" "$W/owned_apps.json"
python3 -I "$HERE/appinfo.py" "$W/appinfo.json"
[ -s "$W/tags.json" ] || curl -sf -A steamed-pi-compat 'https://api.steampowered.com/IStoreService/GetTagList/v1/?language=english' -o "$W/tags.json"
[ "${1:-}" = --quick ] || python3 -I "$HERE/crawl.py"
python3 -I "$HERE/classify.py"
python3 -I "$HERE/report.py"
