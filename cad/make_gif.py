# -*- coding: utf-8 -*-
"""Assemble les images de render_gif.py en docs/img/tvc_demo.gif (avec les angles en surimpression)."""
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "exports", "frames")
OUT = os.path.join(HERE, "..", "docs", "img", os.environ.get("TVC_GIF", "tvc_demo.gif"))
WIDTH = 600


def font(sz):
    for f in ("DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


rows = [l.strip().split(",") for l in open(os.path.join(FRAMES, "angles.csv"))]
f = font(18)
paths = [os.path.join(FRAMES, f"f{int(r[0]):03d}.png") for r in rows]

# Cadre commun à toutes les images : union des zones non blanches + marge
box = None
for p in paths:
    im = Image.open(p).convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
m = 30
box = (max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height))
bw, bh = box[2] - box[0], box[3] - box[1]
if bh > bw:  # module allongé : largeur fixe
    out_w = 420
else:        # cadre carré centré
    c = max(bw, bh)
    cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    box = (cx - c // 2, cy - c // 2, cx + c // 2, cy + c // 2)
    out_w = WIDTH

def crop_white(im, b):
    """Recadre en complétant en blanc si le cadre sort de l'image."""
    out = Image.new("RGB", (b[2] - b[0], b[3] - b[1]), "white")
    out.paste(im, (-b[0], -b[1]))
    return out


frames = []
for p, (k, tx, ty, sx, sy) in zip(paths, rows):
    im = crop_white(Image.open(p).convert("RGB"), box)
    im = im.resize((out_w, out_w * im.height // im.width), Image.LANCZOS)
    canvas = Image.new("RGB", (max(im.width, 420), im.height + 64), "white")
    canvas.paste(im, ((canvas.width - im.width) // 2, 64))
    d = ImageDraw.Draw(canvas)
    d.text((14, 10), f"cardan  θx {float(tx):+5.1f}°  θy {float(ty):+5.1f}°", fill=(30, 30, 30), font=f)
    d.text((14, 36), f"servos  X  {float(sx):+5.1f}°  Y  {float(sy):+5.1f}°", fill=(20, 60, 160), font=f)
    im = canvas
    frames.append(im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE))

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
print(OUT, os.path.getsize(OUT) // 1024, "ko")
