# -*- coding: utf-8 -*-
"""Assemble les images de render_gif.py en docs/img/tvc_demo.gif (avec les angles en surimpression)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "exports", "frames")
OUT = os.path.join(HERE, "..", "docs", "img", "tvc_demo.gif")
SIZE = 600


def font(sz):
    for f in ("DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


rows = [l.strip().split(",") for l in open(os.path.join(FRAMES, "angles.csv"))]
f = font(18)
frames = []
for k, tx, ty, sx, sy in rows:
    im = Image.open(os.path.join(FRAMES, f"f{int(k):03d}.png")).convert("RGB")
    w, h = im.size  # recadrage carré centré sur le module
    c = min(w, h)
    im = im.crop(((w - c) // 2, (h - c) // 2, (w + c) // 2, (h + c) // 2)).resize((SIZE, SIZE), Image.LANCZOS)
    canvas = Image.new("RGB", (SIZE, SIZE + 64), "white")
    canvas.paste(im, (0, 64))
    d = ImageDraw.Draw(canvas)
    d.text((14, 10), f"cardan  θx {float(tx):+5.1f}°  θy {float(ty):+5.1f}°", fill=(30, 30, 30), font=f)
    d.text((14, 36), f"servos  X  {float(sx):+5.1f}°  Y  {float(sy):+5.1f}°", fill=(20, 60, 160), font=f)
    im = canvas
    frames.append(im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE))

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
print(OUT, os.path.getsize(OUT) // 1024, "ko")
