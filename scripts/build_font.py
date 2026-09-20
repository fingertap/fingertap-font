#!/usr/bin/env python3
"""
Build a TTF icon font from SVG files using FontForge.

Must be run with: fontforge -script build_font.py [args]

Usage:
    fontforge -script scripts/build_font.py --input icons/svg --output dist

Reads all .svg files from the input directory and generates a TTF font +
codepoints.json mapping.

Codepoints are STABLE: they come from codepoints.lock.json, a tracked registry
mapping icon name -> codepoint. An icon keeps its codepoint forever, no matter
how many icons are added, renamed or removed around it. New icons are appended
at the next free codepoint starting from U+F534. Codepoints of deleted icons are
tombstoned and never handed to a different icon.
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

# Tracked registry pinning icon name -> codepoint (see module docstring).
DEFAULT_LOCK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "codepoints.lock.json",
)


def load_lock(lock_path: str) -> dict:
    """Load the name -> codepoint registry. Returns {} if it does not exist yet."""
    if not os.path.exists(lock_path):
        return {}

    with open(lock_path, encoding='utf-8') as f:
        data = json.load(f)

    icons = data.get("icons", {})
    lock = {}
    seen = {}
    for name, hex_cp in icons.items():
        cp = int(hex_cp, 16)
        if cp in seen:
            print("ERROR: %s assigns U+%04X to both '%s' and '%s'."
                  % (lock_path, cp, seen[cp], name))
            sys.exit(1)
        seen[cp] = name
        lock[name] = cp
    return lock


def save_lock(lock_path: str, lock: dict):
    """Write the registry back, ordered by codepoint so diffs stay append-only."""
    icons = {
        name: "%04X" % cp
        for name, cp in sorted(lock.items(), key=lambda kv: kv[1])
    }
    data = {
        "_comment": (
            "Permanent name -> codepoint registry. DO NOT reorder or edit existing "
            "entries: they are referenced by user configs (polybar, waybar, terminal, "
            "etc). New icons are appended automatically by scripts/build_font.py. "
            "Entries for deleted icons are kept as tombstones so their codepoint is "
            "never reused by a different icon."
        ),
        "_range_start": "%04X" % START_CODEPOINT,
        "icons": icons,
    }
    with open(lock_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def assign_codepoints(names, lock: dict):
    """Resolve each icon name to its permanent codepoint.

    Known names keep their codepoint. Unknown names are appended at the lowest
    codepoint not present in the registry, so existing icons never shift.
    Mutates and returns `lock`.
    """
    used = set(lock.values())
    next_free = START_CODEPOINT
    added = []

    for name in names:
        if name in lock:
            continue
        while next_free in used:
            next_free += 1
        lock[name] = next_free
        used.add(next_free)
        added.append(name)

    return added


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


def build_font(svg_dir: str, output_dir: str, lock_path: str):
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

    # Resolve stable codepoints from the registry before touching the font
    lock = load_lock(lock_path)
    names = [os.path.splitext(f)[0] for f in svg_files]
    added = assign_codepoints(names, lock)
    if added:
        print("New icon(s) assigned a codepoint: %s"
              % ", ".join("%s -> U+%04X" % (n, lock[n]) for n in added))

    missing = sorted(set(lock) - set(names))
    if missing:
        print("Note: %d codepoint(s) reserved for icons with no SVG present: %s"
              % (len(missing), ", ".join(missing)))

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

    # Import SVGs at their registry-assigned codepoints
    codepoints = {}

    for svg_file in svg_files:
        name = os.path.splitext(svg_file)[0]
        codepoint = lock[name]
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

    # Generate TTF
    ttf_path = os.path.join(output_dir, "fingertap-icons.ttf")
    font.generate(ttf_path)
    print("\nFont generated: %s" % ttf_path)
    print("Glyphs: %d" % len(codepoints))
    if codepoints:
        assigned = [int(h, 16) for h in codepoints.values()]
        print("Range: U+%04X - U+%04X" % (min(assigned), max(assigned)))

    # Persist the registry (appends any newly assigned codepoints)
    save_lock(lock_path, lock)
    print("Registry: %s" % lock_path)

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
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 3em; }
h1 { font-size: 28px; font-weight: 600; letter-spacing: -0.5px; margin-bottom: 6px; }
.subtitle { font-size: 14px; color: #525252; margin-bottom: 2em; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
.icon { background: #171717; border: 1px solid #262626; border-radius: 10px; padding: 1.2em 0.8em; text-align: center; transition: border-color 0.2s; }
.icon:hover { border-color: #525252; }
.glyph { font-family: 'Fingertap Icons'; font-size: 36px; display: block; margin-bottom: 0.6em; color: #fafafa; }
.name { font-size: 12px; color: #a3a3a3; display: block; }
.code { font-size: 11px; color: #525252; display: block; margin-top: 4px; font-family: 'SF Mono', 'Fira Code', monospace; }
</style>
</head>
<body>
  <h1>Fingertap Icons</h1>
  <p class="subtitle">%d icons &middot; U+F534+</p>
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
    parser.add_argument('--lock', '-l', default=DEFAULT_LOCK_PATH,
                        help='Path to the permanent codepoint registry '
                             '(default: codepoints.lock.json in the project root)')
    args = parser.parse_args()

    build_font(args.input, args.output, args.lock)


if __name__ == '__main__':
    main()
