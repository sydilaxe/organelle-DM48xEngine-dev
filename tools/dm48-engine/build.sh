#!/bin/bash
# Build the DM48 Engine patch and its manual from this generator.
#   ./build.sh            -> ../../patches/DM48 Engine  and  ../../docs/DM48 Engine Manual.pdf
# Needs: python3, numpy (tests), Pure Data 0.53+ (tests), Chromium (manual PDF).
set -e
cd "$(dirname "$0")"
OUT="../../patches/DM48 Engine"
rm -rf "$OUT"
python3 gen_all.py "$OUT"
./tload.sh "$OUT" && rm -f "$OUT/t_load.pd"
CHROME=${CHROME:-/opt/pw-browsers/chromium}
if [ -x "$CHROME" ]; then
  python3 make_manual.py shots "../../docs/DM48 Engine Manual.pdf" "$OUT/tunings/TUNINGS.txt"
fi
