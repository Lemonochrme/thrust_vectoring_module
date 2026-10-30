# -*- coding: utf-8 -*-
"""Rendus PNG de l'assemblage (nécessite l'interface graphique FreeCAD).

  xvfb-run -s "-screen 0 1600x1200x24" freecad cad/render_views.py
"""
import os
import FreeCAD as App
import FreeCADGui as Gui

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "docs", "img")
os.makedirs(IMG, exist_ok=True)
SCRIPT = os.path.join(HERE, "tvc_module.py")

VIEWS = [  # (fichier, θx, θy, vue, masquer)
    ("assembly_iso.png", 0, 0, "iso", []),
    ("assembly_tilt.png", 8, -8, "iso", []),
    ("gimbal_detail.png", 10, 0, "front", ["top_plate", "avionics_deck", "esp32c3", "mpu6050", "dist_board",
                                          "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"]),
    ("top_view.png", 0, 0, "top", ["top_plate", "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"]),
    ("servo_bay.png", 0, 0, "iso", ["top_plate", "avionics_deck", "esp32c3", "mpu6050", "dist_board",
                                    "screw_m3_0", "screw_m3_1", "screw_m3_2", "screw_m3_3"]),
]

for fname, tx, ty, view, hidden in VIEWS:
    os.environ.update(TVC_THETA_X=str(tx), TVC_THETA_Y=str(ty), TVC_CHECK="0", TVC_EXPORT="0")
    g = {"__file__": SCRIPT, "__name__": "tvc_module"}
    exec(open(SCRIPT, encoding="utf-8").read(), g)
    doc = g["TVC_DOC"]
    Gui.ActiveDocument = Gui.getDocument(doc.Name)
    for name in hidden:
        doc.getObject(name).ViewObject.Visibility = False
    v = Gui.ActiveDocument.ActiveView
    {"iso": v.viewIsometric, "front": v.viewFront, "top": v.viewTop}[view]()
    Gui.SendMsgToActiveView("ViewFit")
    v.saveImage(os.path.join(IMG, fname), 1400, 1100, "White")
    App.closeDocument(doc.Name)

Gui.getMainWindow().close()
