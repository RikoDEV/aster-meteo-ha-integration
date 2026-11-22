#!/usr/bin/env python3
"""Generate the brand images in custom_components/aster_meteo/brand/.

Home Assistant (2026.3+) shows the images from a custom integration's local
``brand`` folder in the UI: icon.png / logo.png (+ @2x and dark_ variants).

    pip install pillow
    python scripts/make_brand.py

The artwork is drawn from scratch (sun behind a cloud on a sky gradient), it is
not the A-Ster network's trademark.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "custom_components" / "aster_meteo" / "brand"
FONT_BOLD = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
FONT_REG = ["seguisb.ttf", "segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
SS = 4  # supersampling factor


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def icon(size: int) -> Image.Image:
    """Draw the square icon at ``size`` px."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # sky gradient clipped to a rounded square
    grad = Image.new("RGBA", (s, s))
    px = grad.load()
    top, bottom = (63, 169, 245), (21, 101, 192)
    for y in range(s):
        t = y / (s - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(s):
            px[x, y] = color
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)

    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # sun with rays
    cx, cy, r = s * 0.62, s * 0.37, s * 0.15
    for k in range(12):
        a = math.radians(k * 30)
        d.line(
            (
                cx + math.cos(a) * r * 1.35,
                cy + math.sin(a) * r * 1.35,
                cx + math.cos(a) * r * 1.85,
                cy + math.sin(a) * r * 1.85,
            ),
            fill=(255, 214, 90, 255),
            width=int(s * 0.028),
        )
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 201, 60, 255))

    # cloud (with a soft shadow)
    def cloud(draw: ImageDraw.ImageDraw, color: tuple[int, int, int, int], dy: float = 0) -> None:
        y = s * (0.63 + dy)
        draw.rounded_rectangle((s * 0.20, y, s * 0.80, y + s * 0.16), radius=int(s * 0.08), fill=color)
        for ccx, ccy, cr in ((0.37, 0.60, 0.145), (0.56, 0.53, 0.19), (0.70, 0.62, 0.12)):
            draw.ellipse(
                (s * ccx - s * cr, s * (ccy + dy) - s * cr, s * ccx + s * cr, s * (ccy + dy) + s * cr),
                fill=color,
            )

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cloud(ImageDraw.Draw(shadow), (8, 40, 90, 110), dy=0.02)
    shadow = shadow.filter(ImageFilter.GaussianBlur(s * 0.025))
    layer = Image.alpha_composite(shadow, layer)
    cloud(ImageDraw.Draw(layer), (255, 255, 255, 255))

    img = Image.alpha_composite(img, layer)
    return img.resize((size, size), Image.LANCZOS)


def logo(height: int, dark: bool) -> Image.Image:
    """Icon plus the wordmark, ``height`` px tall."""
    ic = icon(height)
    ink = (255, 255, 255, 255) if dark else (13, 43, 69, 255)
    sub = (160, 200, 235, 255) if dark else (21, 101, 192, 255)
    big, small = font(FONT_BOLD, int(height * 0.40)), font(FONT_REG, int(height * 0.2))
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w1 = probe.textlength("A-Ster.pl", font=big)
    w2 = probe.textlength("M E T E O", font=small)
    gap, width = int(height * 0.12), int(height + height * 0.12 + max(w1, w2))
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.paste(ic, (0, 0), ic)
    d = ImageDraw.Draw(img)
    x = height + gap
    d.text((x, height * 0.50), "A-Ster.pl", font=big, fill=ink, anchor="ls")
    d.text((x + height * 0.01, height * 0.74), "M E T E O", font=small, fill=sub, anchor="ls")
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon(256).save(OUT / "icon.png", optimize=True)
    icon(512).save(OUT / "icon@2x.png", optimize=True)
    for dark in (False, True):
        prefix = "dark_" if dark else ""
        logo(256, dark).save(OUT / f"{prefix}logo.png", optimize=True)
        logo(512, dark).save(OUT / f"{prefix}logo@2x.png", optimize=True)
    print("written to", OUT)


if __name__ == "__main__":
    main()
