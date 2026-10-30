# -*- coding: utf-8 -*-
"""Rendus PNG de l'assemblage (nécessite l'interface graphique FreeCAD).

  xvfb-run -s "-screen 0 1600x1200x24" freecad cad/render_views.py
  TVC_MODEL=tvc_compact.py xvfb-run -s "-screen 0 1600x1200x24" freecad cad/render_views.py
"""
import os
import FreeCAD as App
import FreeCADGui as Gui

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "docs", "img")
os.makedirs(IMG, exist_ok=True)
MODEL = os.environ.get("TVC_MODEL", "tvc_module.py")
SCRIPT = os.path.join(HERE, MODEL)

TOP_STACK = ["top_plate", "avionics_deck", "esp32c3", "mpu6050", "dist_board",
             "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"]
VIEWS_BY_MODEL = {  # (fichier, θx, θy, vue, masquer, taille)
    "tvc_module.py": [
        ("assembly_iso.png", 0, 0, "iso", [], (1400, 1100)),
        ("assembly_tilt.png", 8, -8, "iso", [], (1400, 1100)),
        ("gimbal_detail.png", 10, 0, "front", TOP_STACK, (1400, 1100)),
        ("top_view.png", 0, 0, "top", ["top_plate", "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"],
         (1400, 1100)),
        ("servo_bay.png", 0, 0, "iso", TOP_STACK, (1400, 1100)),
    ],
    "tvc_compact.py": [
        ("compact_iso.png", 0, 0, "iso", ["tube_ref"], (1600, 2400)),
        ("compact_inside.png", 8, -8, "iso", ["tube_ref", "bay"], (1600, 2400)),
        ("compact_in_tube.png", 0, 0, "iso", [], (1600, 2400)),
    ],
}
VIEWS = VIEWS_BY_MODEL[MODEL]


def autocrop(path, margin=30):
    """Retire les marges blanches (Pillow, si disponible)."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return
    im = Image.open(path).convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if bb:
        im.crop((max(bb[0] - margin, 0), max(bb[1] - margin, 0), min(bb[2] + margin, im.width),
                 min(bb[3] + margin, im.height))).save(path)

for fname, tx, ty, view, hidden, size in VIEWS:
    os.environ.update(TVC_THETA_X=str(tx), TVC_THETA_Y=str(ty), TVC_CHECK="0", TVC_EXPORT="0")
    g = {"__file__": SCRIPT, "__name__": "tvc_module"}
    exec(open(SCRIPT, encoding="utf-8").read(), g)
    doc = g["TVC_DOC"]
    Gui.ActiveDocument = Gui.getDocument(doc.Name)
    for name in hidden:
        doc.getObject(name).ViewObject.Visibility = False
    v = Gui.getDocument(doc.Name).ActiveView
    {"iso": v.viewIsometric, "front": v.viewFront, "top": v.viewTop}[view]()
    v.fitAll()
    path = os.path.join(IMG, fname)
    v.saveImage(path, size[0], size[1], "White")
    autocrop(path)
    App.closeDocument(doc.Name)

Gui.getMainWindow().close()
