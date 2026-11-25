#!/usr/bin/env python3
"""Regenerate the RConnect Android launcher/notification icons from res/mac-icon.png (1024px).
Needs Pillow:  python3 -m venv v && v/bin/pip install pillow && v/bin/python rconnect-tools/gen-android-icons.py
"""
import os
from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = os.path.join(ROOT, "flutter/android/app/src/main/res")
src = Image.open(os.path.join(ROOT, "res/mac-icon.png")).convert("RGBA")

# density -> (legacy px, adaptive layer px, notification px)
DENS = {"mdpi": (48, 108, 24), "hdpi": (72, 162, 36), "xhdpi": (96, 216, 48),
        "xxhdpi": (144, 324, 72), "xxxhdpi": (192, 432, 96)}

# White glyph (R + waves) = blue channel of the icon (orange background has b<=12; thresholded), clipped by alpha.
r, g, b, a = src.split()
glyph_alpha = ImageChops.multiply(b, a).point(lambda v: 0 if v < 40 else min(255, (v - 40) * 255 // 160))
bbox = glyph_alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
glyph_alpha = glyph_alpha.crop(bbox)


def glyph_canvas(size, fill_ratio):
    """Glyph centred on a transparent size x size canvas, height = fill_ratio * size."""
    gw, gh = glyph_alpha.size
    scale = fill_ratio * size / max(gw, gh)
    m = glyph_alpha.resize((max(1, round(gw * scale)), max(1, round(gh * scale))), Image.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas


for d, (leg, fg, notif) in DENS.items():
    out = os.path.join(RES, "mipmap-" + d)
    icon = src.resize((leg, leg), Image.LANCZOS)
    icon.save(os.path.join(out, "ic_launcher.png"))
    # round: circle mask over the full-bleed icon (fill corners with the edge colour first)
    flat = Image.new("RGBA", src.size, src.getpixel((src.width // 2, 8)))
    flat.alpha_composite(src)
    big = flat.resize((leg * 4, leg * 4), Image.LANCZOS)
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big.width - 1, big.height - 1), fill=255)
    big.putalpha(mask)
    big.resize((leg, leg), Image.LANCZOS).save(os.path.join(out, "ic_launcher_round.png"))
    # adaptive foreground: white glyph inside the 66/108 safe zone
    white = Image.new("RGBA", (fg, fg), (255, 255, 255, 255))
    white.putalpha(glyph_canvas(fg, 0.50))
    white.save(os.path.join(out, "ic_launcher_foreground.png"))
    # notification small icon: white glyph, gray+alpha like upstream
    n = Image.new("LA", (notif, notif), (255, 0))
    n.putalpha(glyph_canvas(notif, 0.80))
    n.save(os.path.join(out, "ic_stat_logo.png"))
print("ok")
