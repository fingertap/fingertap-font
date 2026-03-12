#!/usr/bin/env python3
"""
Build a TTF icon font from SVG files using FontForge.

Must be run with: fontforge -script build_font.py [args]

Usage:
    fontforge -script scripts/build_font.py --input icons/svg --output dist

Reads all .svg files from the input directory, assigns Unicode codepoints
starting from U+F534, and generates a TTF font + codepoints.json mapping.
"""

import argparse
import json
import os
import sys

# FontForge provides its own module when run via `fontforge -script`
try:
    import fontforge
except ImportError:
    print("ERROR: This script must be run with: fontforge -script build_font.py")
    print("       FontForge Python module is not available in regular Python.")
    sys.exit(1)


FONT_NAME = "FingertapIcons"
FONT_FAMILY = "Fingertap Icons"
FONT_FULLNAME = "Fingertap Icons"
FONT_VERSION = "1.0"
FONT_COPYRIGHT = "Custom icon font"

START_CODEPOINT = 0xF534  # Start of our PUA range (avoids Nerd Fonts conflict)
EM_SIZE = 1024


def compute_centroid(glyph):
    """Compute area-weighted centroid of a glyph using the Shoelace formula.

    For each contour, treat the points (on-curve and off-curve) as a polygon,
    compute its signed area and centroid contribution, then combine all contours
    weighted by their absolute area.

    Returns (cx, cy) or None if the glyph has no usable contours.
    """
    layer = glyph.foreground
    total_area = 0.0
    weighted_cx = 0.0
    weighted_cy = 0.0

    for contour in layer:
        points = [(p.x, p.y) for p in contour]
        n = len(points)
        if n < 3:
            continue

        # Shoelace formula
        area = 0.0
        cx = 0.0
        cy = 0.0
        for i in range(n):
            j = (i + 1) % n
            cross = points[i][0] * points[j][1] - points[j][0] * points[i][1]
            area += cross
            cx += (points[i][0] + points[j][0]) * cross
            cy += (points[i][1] + points[j][1]) * cross

        area /= 2.0
        if abs(area) < 0.001:
            continue

        cx /= (6.0 * area)
        cy /= (6.0 * area)

        abs_area = abs(area)
        total_area += abs_area
        weighted_cx += cx * abs_area
        weighted_cy += cy * abs_area

    if total_area > 0:
        return (weighted_cx / total_area, weighted_cy / total_area)
    return None


def build_font(svg_dir: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # Collect SVG files
    svg_files = sorted([
        f for f in os.listdir(svg_dir)
        if f.lower().endswith('.svg')
    ])

    if not svg_files:
        print("No SVG files found in %s" % svg_dir)
        sys.exit(1)

    print("Building font from %d SVG file(s)" % len(svg_files))

    # Create new font
    font = fontforge.font()
    font.fontname = FONT_NAME
    font.familyname = FONT_FAMILY
    font.fullname = FONT_FULLNAME
    font.version = FONT_VERSION
    font.copyright = FONT_COPYRIGHT
    font.encoding = "UnicodeFull"
    font.em = EM_SIZE
    font.ascent = int(EM_SIZE * 0.8)   # 800
    font.descent = int(EM_SIZE * 0.2)  # 200

    # Add a .notdef glyph
    notdef = font.createChar(-1, ".notdef")
    notdef.width = EM_SIZE

    # Import SVGs and assign codepoints
    codepoints = {}
    codepoint = START_CODEPOINT

    for svg_file in svg_files:
        name = os.path.splitext(svg_file)[0]
        svg_path = os.path.join(svg_dir, svg_file)

        # Create glyph at this codepoint
        glyph = font.createChar(codepoint, name)
        glyph.importOutlines(svg_path)

        # Scale to fit em square properly
        bbox = glyph.boundingBox()  # (xmin, ymin, xmax, ymax)
        if bbox != (0, 0, 0, 0):
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            if width > 0 and height > 0:
                # Scale to fit within em square with some padding
                target = EM_SIZE * 0.9  # 90% of em, leaving 5% padding each side
                scale = min(target / width, target / height)

                if abs(scale - 1.0) > 0.01:
                    mat = psMat.scale(scale)
                    glyph.transform(mat)

                # Center using area-weighted centroid (visual center of mass)
                # This ensures asymmetric icons appear visually centered
                target_cx = EM_SIZE / 2.0
                target_cy = (font.ascent - font.descent) / 2.0

                centroid = compute_centroid(glyph)
                if centroid:
                    cx, cy = centroid
                    x_offset = target_cx - cx
                    y_offset = target_cy - cy
                else:
                    # Fallback to bounding box center
                    bbox = glyph.boundingBox()
                    bcx = (bbox[0] + bbox[2]) / 2.0
                    bcy = (bbox[1] + bbox[3]) / 2.0
                    x_offset = target_cx - bcx
                    y_offset = target_cy - bcy

                mat = psMat.translate(x_offset, y_offset)
                glyph.transform(mat)

        glyph.width = EM_SIZE

        hex_cp = "%04X" % codepoint
        codepoints[name] = hex_cp
        print("  U+%s  %s" % (hex_cp, name))
        codepoint += 1

    # Generate TTF
    ttf_path = os.path.join(output_dir, "fingertap-icons.ttf")
    font.generate(ttf_path)
    print("\nFont generated: %s" % ttf_path)
    print("Glyphs: %d" % len(codepoints))
    print("Range: U+%04X - U+%04X" % (START_CODEPOINT, codepoint - 1))

    # Write codepoint mapping
    json_path = os.path.join(output_dir, "codepoints.json")
    with open(json_path, 'w') as f:
        json.dump(codepoints, f, indent=2)
    print("Codepoints: %s" % json_path)

    # Generate preview HTML
    generate_preview(codepoints, output_dir)

    # Generate copyable cheatsheet
    generate_cheatsheet(codepoints, output_dir)

    font.close()


def generate_preview(codepoints: dict, output_dir: str):
    """Generate a simple HTML preview page."""
    rows = ""
    for name, hex_cp in sorted(codepoints.items(), key=lambda x: x[1]):
        char = "&#x%s;" % hex_cp
        rows += '      <div class="icon"><span class="glyph">%s</span><span class="name">%s</span><span class="code">U+%s</span></div>\n' % (char, name, hex_cp)

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Fingertap Icons Preview</title>
<style>
@font-face {
  font-family: 'Fingertap Icons';
  src: url('fingertap-icons.ttf') format('truetype');
}
body { font-family: sans-serif; background: #1a1a2e; color: #eee; padding: 2em; }
h1 { color: #e94560; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1em; }
.icon { background: #16213e; border-radius: 8px; padding: 1em; text-align: center; }
.glyph { font-family: 'Fingertap Icons'; font-size: 48px; display: block; margin-bottom: 0.5em; }
.name { font-size: 12px; color: #a0a0a0; display: block; }
.code { font-size: 11px; color: #666; display: block; margin-top: 4px; }
</style>
</head>
<body>
  <h1>Fingertap Icons</h1>
  <p>%d icons | Range: U+F534+</p>
  <div class="grid">
%s
  </div>
</body>
</html>""" % (len(codepoints), rows)

    preview_path = os.path.join(output_dir, "preview.html")
    with open(preview_path, 'w') as f:
        f.write(html)
    print("Preview: %s" % preview_path)


def generate_cheatsheet(codepoints: dict, output_dir: str):
    """Generate a plain-text cheatsheet with copyable Unicode characters."""
    lines = []
    lines.append("Fingertap Icons Cheatsheet")
    lines.append("=" * 40)
    lines.append("")
    lines.append("Copy the character from the 'Char' column.")
    lines.append("Use in terminal/config after installing the font.")
    lines.append("")
    lines.append("%-16s  %-6s  %-8s  %s" % ("Name", "Char", "Unicode", "Escape"))
    lines.append("-" * 50)

    for name, hex_cp in sorted(codepoints.items(), key=lambda x: x[1]):
        char = chr(int(hex_cp, 16))
        escape = "\\u%s" % hex_cp
        lines.append("%-16s  %s     U+%-6s  %s" % (name, char, hex_cp, escape))

    lines.append("")
    lines.append("Font: fingertap-icons.ttf")
    lines.append("Install: cp dist/fingertap-icons.ttf ~/.local/share/fonts/ && fc-cache -fv")

    text = "\n".join(lines) + "\n"

    cheatsheet_path = os.path.join(output_dir, "cheatsheet.txt")
    with open(cheatsheet_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Cheatsheet: %s" % cheatsheet_path)


def main():
    parser = argparse.ArgumentParser(description='Build TTF icon font from SVGs')
    parser.add_argument('--input', '-i', default='icons/svg',
                        help='Input directory with SVG files (default: icons/svg)')
    parser.add_argument('--output', '-o', default='dist',
                        help='Output directory (default: dist)')
    args = parser.parse_args()

    build_font(args.input, args.output)


if __name__ == '__main__':
    main()
