# -*- coding: utf-8 -*-
"""Images d'une animation du module : le moteur décrit un cône de 10° (balayage circulaire).

  xvfb-run -s "-screen 0 1600x1200x24" freecad cad/render_gif.py
  puis : python3 cad/make_gif.py
"""
import math
import os

import FreeCAD as App
import FreeCADGui as Gui

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.environ.get("TVC_FRAMES_DIR", os.path.join(HERE, "exports", "frames"))
N = int(os.environ.get("TVC_FRAMES", "48"))
os.makedirs(FRAMES, exist_ok=True)

SCRIPT = os.path.join(HERE, "tvc_module.py")
os.environ.update(TVC_CHECK="0", TVC_EXPORT="0", TVC_THETA_X="0", TVC_THETA_Y="0")
g = {"__file__": SCRIPT, "__name__": "tvc_module"}
exec(open(SCRIPT, encoding="utf-8").read(), g)
doc = g["TVC_DOC"]
items = g["build_items"]()
amp = g["P"]["max_tilt"]

# On retire le haut de l'empilage pour voir les servos, palonniers et biellettes
for name in ("top_plate", "avionics_deck", "esp32c3", "mpu6050", "dist_board",
             "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"):
    doc.getObject(name).ViewObject.Visibility = False

Gui.ActiveDocument = Gui.getDocument(doc.Name)
view = Gui.ActiveDocument.ActiveView
view.viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
moving = [i.name for i in items if i.group != "static"]

with open(os.path.join(FRAMES, "angles.csv"), "w") as log:
    for k in range(N):
        a = 2 * math.pi * k / N
        tx, ty = amp * math.sin(a), amp * math.cos(a)
        shapes, servo = g["pose"](items, tx, ty)
        for name in moving:
            doc.getObject(name).Shape = shapes[name]
        doc.recompute()
        Gui.updateGui()
        view.saveImage(os.path.join(FRAMES, f"f{k:03d}.png"), 900, 900, "White")
        log.write(f"{k},{tx:.2f},{ty:.2f},{servo['X']:.2f},{servo['Y']:.2f}\n")

App.closeDocument(doc.Name)  # évite la demande d'enregistrement qui bloque la fermeture
Gui.getMainWindow().close()
