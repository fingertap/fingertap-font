#!/bin/bash
#
# Build pipeline: images → SVG → TTF font
#
# Usage:
#   ./scripts/build.sh [threshold]
#
# Input:
#   icons/png/*.{png,jpg,jpeg}  - Image icon files
#   icons/svg/*.svg             - Pre-made SVG files (bypass vectorization)
#
# Output:
#   dist/fingertap-icons.ttf  - The icon font
#   dist/codepoints.json      - Unicode codepoint mapping
#   dist/preview.html         - Browser preview page

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

THRESHOLD="${1:-50}"

echo "=== Fingertap Icons Build ==="
echo ""

# Step 1: Vectorize images that don't already have a corresponding SVG
IMG_COUNT=0
VECTORIZE_COUNT=0
for img in icons/png/*.png icons/png/*.jpg icons/png/*.jpeg; do
    [ -f "$img" ] || continue
    IMG_COUNT=$((IMG_COUNT + 1))
    name=$(basename "$img")
    name="${name%.*}"
    if [ ! -f "icons/svg/${name}.svg" ]; then
        VECTORIZE_COUNT=$((VECTORIZE_COUNT + 1))
    fi
done

if [ "$VECTORIZE_COUNT" -gt 0 ]; then
    echo "--- Step 1: Vectorize images ($VECTORIZE_COUNT of $IMG_COUNT, skipping those with existing SVGs) ---"
    TMPDIR=$(mktemp -d)
    for img in icons/png/*.png icons/png/*.jpg icons/png/*.jpeg; do
        [ -f "$img" ] || continue
        name=$(basename "$img")
        name="${name%.*}"
        if [ ! -f "icons/svg/${name}.svg" ]; then
            cp "$img" "$TMPDIR/"
        fi
    done
    python3 scripts/vectorize.py -i "$TMPDIR" -o icons/svg -t "$THRESHOLD"
    rm -rf "$TMPDIR"
    echo ""
else
    echo "--- Step 1: No images to vectorize (all have SVGs or no images found) ---"
    echo ""
fi

# Step 2: Build font from SVGs
SVG_COUNT=$(find icons/svg -name '*.svg' 2>/dev/null | wc -l)
if [ "$SVG_COUNT" -eq 0 ]; then
    echo "ERROR: No SVG files found in icons/svg/"
    echo "       Place image files in icons/png/ or SVG files in icons/svg/"
    exit 1
fi

echo "--- Step 2: Build font ($SVG_COUNT SVGs) ---"
fontforge -script scripts/build_font.py -i icons/svg -o dist
echo ""

echo "=== Done ==="
echo ""
cat dist/cheatsheet.txt
echo ""
echo "Install: cp dist/fingertap-icons.ttf ~/.local/share/fonts/ && fc-cache -fv"
