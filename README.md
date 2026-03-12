# Fingertap Icons

Custom icon font for status bar display. Uses Unicode Private Use Area (U+F534+) to avoid conflicts with Nerd Fonts.

## Quick Start

```bash
# 1. Put SVG icons in icons/svg/
#    (Recommend: download monochrome SVGs from https://simpleicons.org)
mkdir -p icons/svg
# Example: curl -o icons/svg/telegram.svg https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/telegram.svg

# 2. Build
bash scripts/build.sh

# 3. Install
cp dist/fingertap-icons.ttf ~/.local/share/fonts/ && fc-cache -fv
```

## Input Requirements

Place SVG files in `icons/svg/`. File naming rules:

- Lowercase alphanumeric + hyphens: `feishu.svg`, `my-app.svg`
- Monochrome, single-color SVGs work best
- Any viewBox size is fine — the build script auto-scales to fit

PNG fallback: place PNGs in `icons/png/`. They will be auto-vectorized via potrace for icons without a corresponding SVG. Note: this only works well for simple silhouette shapes, not colorful logos.

## Output

After `bash scripts/build.sh`:

- `dist/fingertap-icons.ttf` — the font file
- `dist/codepoints.json` — name → Unicode mapping
- `dist/cheatsheet.txt` — copyable character reference
- `dist/preview.html` — browser preview page

## Codepoint Range

U+F534 onwards (BMP Private Use Area). Does not conflict with Nerd Fonts, Powerline, Font Awesome, Devicons, Codicons, or Octicons.

## Dependencies

- `fontforge` with Python bindings (`apt install fontforge python3-fontforge`)
- `potrace` (`apt install potrace`) — only needed for PNG vectorization
- `imagemagick` (`apt install imagemagick`) — only needed for PNG vectorization
