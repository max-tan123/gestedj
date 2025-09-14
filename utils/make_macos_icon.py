#!/usr/bin/env python3
"""
Generate a macOS .icns from a source PNG with an automatic rounded (squircle) mask.

- Input: square PNG (recommended 1024x1024 or larger)
- Output: .iconset directory and .icns file next to it

Usage:
  python utils/make_macos_icon.py gestedj_logo1.png --out gestedj_logo1.icns

Notes:
- The mask approximates the macOS app icon squircle using the superellipse
  formula |x/a|^n + |y/b|^n = 1 with n≈5.5 which closely matches Big Sur style.
- If the input is not square, it will be centered on a square canvas with
  transparent padding to preserve the full image without distortion.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ICON_SIZES = [
    (16, False), (16, True),
    (32, False), (32, True),
    (128, False), (128, True),
    (256, False), (256, True),
    (512, False), (512, True),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create rounded macOS icns from PNG.")
    parser.add_argument("source", type=Path, help="Source PNG (preferably 1024x1024 square)")
    parser.add_argument("--out", type=Path, default=None, help="Output .icns path")
    parser.add_argument("--keep-iconset", action="store_true", help="Keep the intermediate .iconset directory")
    return parser.parse_args()


def ensure_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    if width == height:
        return image
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    x = (side - width) // 2
    y = (side - height) // 2
    canvas.paste(image, (x, y))
    return canvas


def make_squircle_mask(size: int) -> Image.Image:
    """Create a squircle-like alpha mask sized size×size.

    We approximate Apple's squircle using a superellipse with exponent ~5.5 and
    a small inset to avoid edge clipping at small sizes.
    """
    n = 5.5
    inset = max(1, round(size * 0.03))
    a = b = (size - 2 * inset) / 2.0

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    # Rasterize by plotting horizontal spans
    cx = cy = size / 2.0
    for iy in range(size):
        y = iy + 0.5
        dy = y - cy
        # Solve for x: |x/a|^n + |y/b|^n = 1
        t = 1.0 - (abs(dy) / b) ** n
        if t <= 0:
            continue
        dx = (t ** (1.0 / n)) * a
        x0 = math.floor(cx - dx)
        x1 = math.ceil(cx + dx)
        draw.rectangle((x0, iy, x1, iy), fill=255)
    return mask


def apply_mask(image: Image.Image) -> Image.Image:
    side = max(image.size)
    image = image.resize((side, side), Image.LANCZOS)
    mask = make_squircle_mask(side)
    rounded = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    rounded.paste(image, (0, 0), mask)
    return rounded


def save_iconset(rounded: Image.Image, base_path: Path) -> Path:
    iconset_dir = base_path.with_suffix("").with_name(base_path.stem + ".iconset")
    if iconset_dir.exists():
        for child in iconset_dir.iterdir():
            child.unlink()
    else:
        iconset_dir.mkdir(parents=True)

    for size, is_2x in ICON_SIZES:
        output_size = size * (2 if is_2x else 1)
        resized = rounded.resize((output_size, output_size), Image.LANCZOS)
        suffix = "@2x" if is_2x else ""
        name_map = {
            16: "icon_16x16",
            32: "icon_32x32",
            128: "icon_128x128",
            256: "icon_256x256",
            512: "icon_512x512",
        }
        filename = f"{name_map[size]}{suffix}.png"
        resized.save(iconset_dir / filename, format="PNG")

    return iconset_dir


def build_icns(iconset_dir: Path, out_icns: Path) -> None:
    # Use iconutil if available
    exit_code = os.system(f"iconutil -c icns '{iconset_dir}' -o '{out_icns}' >/dev/null 2>&1")
    if exit_code != 0:
        # Fallback to png2icns if installed
        pngs = " ".join(str(p) for p in sorted(iconset_dir.glob("*.png")))
        exit_code = os.system(f"png2icns '{out_icns}' {pngs} >/dev/null 2>&1")
        if exit_code != 0:
            raise RuntimeError("Neither iconutil nor png2icns succeeded. Ensure Xcode command line tools are installed.")


def main() -> int:
    args = parse_args()
    src = args.source
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr)
        return 2

    img = Image.open(src).convert("RGBA")
    img = ensure_square(img)
    rounded = apply_mask(img)

    out_icns = args.out or src.with_suffix(".icns")
    iconset_dir = save_iconset(rounded, out_icns)
    build_icns(iconset_dir, out_icns)

    if not args.keep_iconset:
        # Clean up iconset to reduce clutter
        for p in iconset_dir.glob("*"):
            p.unlink()
        iconset_dir.rmdir()

    print(f"Wrote {out_icns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


