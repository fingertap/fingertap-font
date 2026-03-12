#!/usr/bin/env python3
"""
Vectorize PNG icons to SVG for font generation.

Input requirements:
  - PNG files in the input directory
  - File naming: <icon-name>.png (e.g., feishu.png, wechat.png)
  - Icon name must be lowercase, alphanumeric + hyphens only
  - Recommended: square images, at least 128x128 px, with transparent background
  - The icon should be a simple, recognizable silhouette shape

Pipeline: PNG → grayscale → threshold → BMP → potrace → SVG (1024x1024)
"""

import argparse
import os
import subprocess
import sys
import re


def validate_filename(name: str) -> bool:
    return bool(re.match(r'^[a-z0-9][a-z0-9-]*$', name))


def vectorize_png(png_path: str, svg_path: str, threshold: int = 50) -> bool:
    """Convert a PNG to a monochrome SVG using ImageMagick + potrace."""
    basename = os.path.basename(png_path)
    name = os.path.splitext(basename)[0]

    if not validate_filename(name):
        print(f"  SKIP {basename}: invalid name (use lowercase a-z, 0-9, hyphens)")
        return False

    bmp_path = svg_path.replace('.svg', '.bmp')

    try:
        # Check if image has alpha channel
        result = subprocess.run(
            ['identify', '-format', '%[channels]', png_path],
            capture_output=True, text=True, check=True
        )
        has_alpha = 'a' in result.stdout.lower()

        if has_alpha:
            # For icons with alpha, try two strategies and pick the better one:
            #
            # 1. Grayscale: flatten → gray → threshold
            #    Pros: preserves internal luminance detail
            #    Cons: loses bright-colored regions (e.g., green on feishu)
            #
            # 2. Alpha: extract alpha channel as shape
            #    Pros: captures full silhouette regardless of color
            #    Cons: loses all internal detail
            #
            # We generate both BMPs, measure their black pixel coverage,
            # and pick the one with more coverage (more of the icon preserved).

            bmp_gray = bmp_path + '.gray.bmp'
            bmp_alpha = bmp_path + '.alpha.bmp'

            # Grayscale approach
            subprocess.run([
                'convert', png_path,
                '-resize', '1024x1024',
                '-background', 'white',
                '-flatten',
                '-colorspace', 'Gray',
                '-threshold', f'{threshold}%',
                f'BMP3:{bmp_gray}'
            ], check=True, capture_output=True)

            # Alpha approach
            subprocess.run([
                'convert', png_path,
                '-resize', '1024x1024',
                '-alpha', 'extract',
                '-negate',
                '-threshold', f'{threshold}%',
                f'BMP3:{bmp_alpha}'
            ], check=True, capture_output=True)

            # Compare: lower mean = more black pixels = more icon coverage
            def get_mean(path):
                r = subprocess.run(
                    ['identify', '-format', '%[mean]', f'BMP3:{path}'],
                    capture_output=True, text=True, check=True
                )
                return float(r.stdout.strip())

            mean_gray = get_mean(bmp_gray)
            mean_alpha = get_mean(bmp_alpha)

            # Pick the one with more black pixels (lower mean)
            if mean_gray < 65000 and mean_gray <= mean_alpha:
                os.rename(bmp_gray, bmp_path)
                os.remove(bmp_alpha)
            else:
                os.rename(bmp_alpha, bmp_path)
                os.remove(bmp_gray)
        else:
            # No alpha: use luminance-based threshold
            subprocess.run([
                'convert', png_path,
                '-resize', '1024x1024',
                '-colorspace', 'Gray',
                '-threshold', f'{threshold}%',
                f'BMP3:{bmp_path}'
            ], check=True, capture_output=True)

        # Step 2: BMP → SVG via potrace
        # -s = SVG output, -W/H set dimensions, --flat = no grouping
        subprocess.run([
            'potrace', bmp_path,
            '-s',                   # SVG output
            '-W', '1024', '-H', '1024',  # output size
            '--flat',               # flat path, no grouping
            '-o', svg_path
        ], check=True, capture_output=True)

        # Clean up temp BMP
        os.remove(bmp_path)

        print(f"  OK   {basename} → {os.path.basename(svg_path)}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  FAIL {basename}: {e.stderr.decode().strip()}")
        if os.path.exists(bmp_path):
            os.remove(bmp_path)
        return False


def vectorize_directory(png_dir: str, svg_dir: str, threshold: int = 50) -> list[str]:
    """Vectorize all PNGs in a directory. Returns list of generated SVG paths."""
    os.makedirs(svg_dir, exist_ok=True)

    png_files = sorted([
        f for f in os.listdir(png_dir)
        if f.lower().endswith('.png')
    ])

    if not png_files:
        print(f"No PNG files found in {png_dir}")
        return []

    print(f"Vectorizing {len(png_files)} PNG(s) from {png_dir}")
    print(f"  threshold={threshold}%")
    print()

    results = []
    for png_file in png_files:
        name = os.path.splitext(png_file)[0]
        png_path = os.path.join(png_dir, png_file)
        svg_path = os.path.join(svg_dir, f'{name}.svg')
        if vectorize_png(png_path, svg_path, threshold):
            results.append(svg_path)

    print(f"\n{len(results)}/{len(png_files)} icons vectorized successfully.")
    return results


def main():
    parser = argparse.ArgumentParser(description='Vectorize PNG icons to SVG')
    parser.add_argument('--input', '-i', default='icons/png',
                        help='Input directory with PNG files (default: icons/png)')
    parser.add_argument('--output', '-o', default='icons/svg',
                        help='Output directory for SVG files (default: icons/svg)')
    parser.add_argument('--threshold', '-t', type=int, default=50,
                        help='Binarization threshold 0-100 (default: 50). '
                             'Lower = more detail, higher = simpler shapes.')
    args = parser.parse_args()

    vectorize_directory(args.input, args.output, args.threshold)


if __name__ == '__main__':
    main()
