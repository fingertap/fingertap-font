#!/bin/bash
#
# Build pipeline: PNG → SVG → TTF font
#
# Usage:
#   ./scripts/build.sh [--threshold 50]
#
# Input:
#   icons/png/*.png   - PNG icon files (see README for requirements)
#   icons/svg/*.svg   - Pre-made SVG files (optional, bypass vectorization)
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

# Step 1: Vectorize PNGs that don't already have a corresponding SVG
PNG_COUNT=0
VECTORIZE_COUNT=0
for png in icons/png/*.png; do
    [ -f "$png" ] || continue
    PNG_COUNT=$((PNG_COUNT + 1))
    name=$(basename "$png" .png)
    if [ ! -f "icons/svg/${name}.svg" ]; then
        VECTORIZE_COUNT=$((VECTORIZE_COUNT + 1))
    fi
done

if [ "$VECTORIZE_COUNT" -gt 0 ]; then
    echo "--- Step 1: Vectorize PNGs ($VECTORIZE_COUNT of $PNG_COUNT, skipping those with existing SVGs) ---"
    # Only vectorize PNGs without corresponding SVGs
    TMPDIR=$(mktemp -d)
    for png in icons/png/*.png; do
        [ -f "$png" ] || continue
        name=$(basename "$png" .png)
        if [ ! -f "icons/svg/${name}.svg" ]; then
            cp "$png" "$TMPDIR/"
        fi
    done
    python3 scripts/vectorize.py -i "$TMPDIR" -o icons/svg -t "$THRESHOLD"
    rm -rf "$TMPDIR"
    echo ""
else
    echo "--- Step 1: No PNGs to vectorize (all have SVGs or no PNGs found) ---"
    echo ""
fi

# Step 2: Build font from SVGs
SVG_COUNT=$(find icons/svg -name '*.svg' 2>/dev/null | wc -l)
if [ "$SVG_COUNT" -eq 0 ]; then
    echo "ERROR: No SVG files found in icons/svg/"
    echo "       Place PNG files in icons/png/ or SVG files in icons/svg/"
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
