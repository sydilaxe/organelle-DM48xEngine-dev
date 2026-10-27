#!/bin/bash
# Package the patches for a release:  tools/package.sh VERSION  ->  dist/*.zip + the manual PDF
# Each zip holds folders ready to copy into the Organelle's Patches folder.
set -e
cd "$(dirname "$0")/.."
VERSION="${1:-dev}"
DIST=dist
STAGE="$DIST/stage"
rm -rf "$DIST"
mkdir -p "$STAGE"

pack() {   # pack NAME folder...
  local name="$1"; shift
  rm -rf "$STAGE"/*
  for f in "$@"; do cp -r "patches/$f" "$STAGE/"; done
  [ -d "$STAGE/DM48 Engine" ] && printf 'DM48 Engine %s\n' "$VERSION" > "$STAGE/DM48 Engine/VERSION.txt"
  (cd "$STAGE" && zip -qr "../${name}-${VERSION}.zip" .)
}

pack DM48_Engine   "DM48 Engine"
cp "docs/DM48 Engine Manual.pdf" "$DIST/DM48_Engine_Manual-${VERSION}.pdf"
rm -rf "$STAGE"
ls -l "$DIST"
