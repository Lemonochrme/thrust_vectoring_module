# -*- coding: utf-8 -*-
"""
Module de poussée vectorielle (TVC) - prototype de banc pour moteur D9 factice.

Script FreeCAD (atelier Part), entièrement paramétrique.

Utilisation :
  * en ligne de commande :  freecadcmd cad/tvc_module.py
  * dans FreeCAD (GUI)    :  Macro > Exécuter, ou exec(open(".../tvc_module.py").read())
  * via un MCP FreeCAD    :  outil `execute_code` avec le contenu de ce fichier

Variables d'environnement optionnelles :
  TVC_THETA_X / TVC_THETA_Y  pose du cardan en degrés (défaut 0 / 0)
  TVC_OUT                    dossier de sortie (défaut : cad/exports)
  TVC_CHECK=0                désactive la vérification des interférences
  TVC_EXPORT=0               désactive les exports STEP / STL / FCStd

Repère : Z vers l'avant de la fusée (buse vers -Z), origine au centre du cardan.
  - axe interne (support moteur / bague)  : X  -> servo "X" (biellette en +Y)
  - axe externe (bague / châssis)         : Y  -> servo "Y" (biellette en +X)
Unités : mm, degrés.
"""
import math
import os

import FreeCAD as App
import Part

V = App.Vector

# --------------------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------------------
P = dict(
    # Moteur D9 factice (gabarit)
    motor_d=24.0, motor_l=70.0, motor_top_z=35.0,        # pivot à mi-longueur du moteur
    # Support moteur (cardan interne)
    mm_bore=24.4, mm_wall=2.0, mm_bottom_z=-22.0, mm_cap=2.4, mm_vent_d=10.0,
    inner_boss_d=9.0, inner_boss_r=20.5,                  # bossage d'axe X (côté extérieur)
    arm_z0=12.5, arm_z1=18.0, arm_w=7.0, arm_boss_d=7.0,  # bras de biellette
    rod_r=26.0,                                           # rayon d'attache des biellettes
    stud_ball_d=4.8, ball_z=21.5,                         # rotule M2 sur le bras
    set_screw_z=-15.0,                                    # vis de maintien du moteur (M3 nylon)
    # Bague de cardan (externe)
    ring_ri=22.0, ring_ro=26.0, ring_h=8.0, ring_xboss_d=10.0, ring_yboss_d=9.0,
    outer_boss_r=30.5,
    # Pivots : roulement MR63ZZ (3x6x2.5) + goupille 3x10 + cale 3x6x0.5
    brg_od=6.0, brg_id=3.0, brg_w=2.5, pin_d=3.0, pin_l=10.0, pin_depth=6.0,
    shim_t=0.5, pass_d=4.0,
    # Châssis
    frame_ri=31.0, frame_ro=38.0, frame_z0=-5.0, frame_z1=5.0,
    col_r=34.5, col_d=7.0,                                # colonnes à 45°
    insert_d=4.0, insert_depth=8.0, m3_clear=3.4, m3_head_d=6.0, m3_head_h=3.0,
    # Plateau servos
    deck_z0=42.0, deck_t=3.0, deck_rod_hole_d=14.0, deck_center_hole_d=16.0,
    # Servo MG90S
    sv_l=22.8, sv_w=12.2, sv_h=22.5, sv_tab_ext=4.85, sv_tab_z0=15.7, sv_tab_t=2.5,
    sv_tab_hole_d=2.0, sv_tab_hole_pitch=27.5, sv_shaft_off=6.0,
    sv_gear_h=4.0, sv_spline_d=4.8, sv_spline_h=3.0,
    horn_r=11.0, horn_hub_d=7.0, horn_t=2.0,
    post_t=3.0, post_pilot_d=1.6,
    # Plateau avionique
    avio_z0=62.0, avio_t=3.0,
    # Platine supérieure / interface banc
    top_z0=80.0, top_t=4.0, bench_m4_r=22.0, bench_m4_d=4.4, bench_center_d=6.5,
    # Électronique
    esp_l=22.5, esp_w=18.0, esp_t=1.0, imu_l=21.0, imu_w=16.0, imu_t=1.6,
    imu_hole_dx=7.5, imu_hole_dy=5.0, imu_standoff=4.0,
    dist_l=20.0, dist_w=28.0, dist_t=1.6, dist_standoff=3.0,
    # Débattement
    max_tilt=10.0,
)

R_OUT = P["frame_ro"]

COLORS = {
    "print": (0.95, 0.55, 0.10), "print2": (0.20, 0.45, 0.85), "frame": (0.25, 0.25, 0.28),
    "motor": (0.85, 0.80, 0.70), "servo": (0.10, 0.25, 0.70), "horn": (0.95, 0.95, 0.95),
    "steel": (0.75, 0.76, 0.78), "brass": (0.80, 0.65, 0.25), "pcb_blue": (0.10, 0.30, 0.65),
    "pcb_black": (0.08, 0.08, 0.08), "pcb_green": (0.10, 0.45, 0.20), "chip": (0.15, 0.15, 0.15),
}


# --------------------------------------------------------------------------------------
# Outils géométriques
# --------------------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p0, p1):
    d = p1 - p0
    return Part.makeCylinder(r, d.Length, p0, V(d.x, d.y, d.z).normalize())


def cylz(r, z0, z1, x=0.0, y=0.0):
    return cyl(r, V(x, y, z0), V(x, y, z1))


def axis_vec(axis, a, off=(0.0, 0.0)):
    """Point à la coordonnée a le long de l'axe 'x'/'y'/'z', décalé de off dans les 2 autres."""
    u, w = off
    return {"x": V(a, u, w), "y": V(u, a, w), "z": V(u, w, a)}[axis]


def cyl_ax(r, axis, a0, a1, off=(0.0, 0.0)):
    return cyl(r, axis_vec(axis, a0, off), axis_vec(axis, a1, off))


def ring(ri, ro, z0, z1):
    return cylz(ro, z0, z1).cut(cylz(ri, z0 - 1, z1 + 1))


def fuse(shapes):
    s = shapes[0].fuse(shapes[1:]) if len(shapes) > 1 else shapes[0]
    return s.removeSplitter()


def xform(shape, pl):
    s = shape.copy()
    s.Placement = pl.multiply(s.Placement)
    return s


def rot_about(center, axis, deg):
    r = App.Rotation(axis, deg)
    return App.Placement(center - r.multVec(center), r)


def rot_from_axes(ex, ey, ez):
    """Rotation qui envoie les axes locaux x, y, z sur ex, ey, ez (vecteurs unitaires)."""
    m = App.Matrix(ex.x, ey.x, ez.x, 0, ex.y, ey.y, ez.y, 0, ex.z, ey.z, ez.z, 0, 0, 0, 0, 1)
    return App.Rotation(m)


def polar(r, deg):
    return math.cos(math.radians(deg)) * r, math.sin(math.radians(deg)) * r


COL_ANGLES = (45.0, 135.0, 225.0, 315.0)


def col_xy(a):
    return polar(P["col_r"], a)


# --------------------------------------------------------------------------------------
# Pièces imprimées
# --------------------------------------------------------------------------------------
def make_motor_mount():
    """Cardan interne : tube moteur + bossages d'axe X + 2 bras de biellette."""
    ro = P["mm_bore"] / 2 + P["mm_wall"]
    z_top = P["motor_top_z"] + P["mm_cap"]
    tube = cylz(ro, P["mm_bottom_z"], z_top)
    parts = [tube]
    # Bossages de pivot (axe X)
    for s in (1, -1):
        parts.append(cyl_ax(P["inner_boss_d"] / 2, "x", s * (ro - 1.0), s * P["inner_boss_r"]))
    # Bras de biellette : +Y (servo X) et +X (servo Y)
    z0, z1, w = P["arm_z0"], P["arm_z1"], P["arm_w"]
    rr = P["rod_r"]
    parts += [box(-w / 2, w / 2, ro - 1.0, rr, z0, z1), cylz(P["arm_boss_d"] / 2, z0, z1, 0, rr)]
    parts += [box(ro - 1.0, rr, -w / 2, w / 2, z0, z1), cylz(P["arm_boss_d"] / 2, z0, z1, rr, 0)]
    # Renforts sous les bras
    for (ax, sgn) in (("y", 1), ("x", 1)):
        pts = [V(0, ro - 1.0, z0), V(0, ro + 7.0, z0), V(0, ro - 1.0, z0 - 8.0), V(0, ro - 1.0, z0)]
        rib = Part.Face(Part.makePolygon(pts)).extrude(V(2.4, 0, 0))
        rib = xform(rib, App.Placement(V(-1.2, 0, 0), App.Rotation()))
        if ax == "x":
            rib = xform(rib, App.Placement(V(), App.Rotation(V(0, 0, 1), -90)))
        parts.append(rib)
    # Bossage de vis de maintien moteur (-Y)
    parts.append(cyl_ax(4.0, "y", -(ro - 1.0), -(ro + 3.0), (0, P["set_screw_z"])))
    body = fuse(parts)
    # Perçages
    cuts = [cylz(P["mm_bore"] / 2, P["mm_bottom_z"] - 1, P["motor_top_z"]),
            cylz(P["mm_vent_d"] / 2, P["motor_top_z"] - 1, z_top + 1)]
    for s in (1, -1):  # trous de goupille
        cuts.append(cyl_ax(P["pin_d"] / 2, "x", s * P["inner_boss_r"], s * (P["inner_boss_r"] - P["pin_depth"])))
    for (x, y) in ((0, rr), (rr, 0)):  # taraudage M2 des rotules
        cuts.append(cylz(0.9, z0 - 1, z1 + 1, x, y))
    cuts.append(cyl_ax(1.25, "y", -(ro - 2.0), -(ro + 4.0), (0, P["set_screw_z"])))  # M3 (taraudé)
    return body.cut(cuts)


def make_gimbal_ring():
    """Cardan externe : bague, roulements de l'axe X, goupilles de l'axe Y."""
    h = P["ring_h"]
    parts = [ring(P["ring_ri"], P["ring_ro"], -h / 2, h / 2)]
    for s in (1, -1):
        parts.append(cyl_ax(P["ring_xboss_d"] / 2, "x", s * (P["inner_boss_r"] + P["shim_t"]), s * P["ring_ro"]))
        parts.append(cyl_ax(P["ring_yboss_d"] / 2, "y", s * (P["ring_ri"] + 0.5), s * P["outer_boss_r"]))
    body = fuse(parts)
    r_in = P["inner_boss_r"] + P["shim_t"]
    cuts = []
    for s in (1, -1):
        cuts.append(cyl_ax(P["brg_od"] / 2, "x", s * (r_in - 0.1), s * (r_in + P["brg_w"])))
        cuts.append(cyl_ax(P["pass_d"] / 2, "x", s * (r_in + 1.0), s * (P["ring_ro"] + 1.0)))
        cuts.append(cyl_ax(P["pin_d"] / 2, "y", s * P["outer_boss_r"] + s * 0.1,
                           s * (P["outer_boss_r"] - P["pin_depth"])))
    return body.cut(cuts)


def make_frame():
    """Châssis inférieur : anneau porte-roulements de l'axe Y + 4 colonnes."""
    z0, z1 = P["frame_z0"], P["frame_z1"]
    parts = [ring(P["frame_ri"], P["frame_ro"], z0, z1)]
    for a in COL_ANGLES:
        x, y = col_xy(a)
        parts.append(cylz(P["col_d"] / 2, z0, P["deck_z0"], x, y))
    body = fuse(parts).common(cylz(R_OUT, z0 - 1, P["deck_z0"] + 1))
    cuts = []
    for s in (1, -1):
        r_in = P["frame_ri"]
        cuts.append(cyl_ax(P["brg_od"] / 2, "y", s * (r_in - 0.1), s * (r_in + P["brg_w"])))
        cuts.append(cyl_ax(P["pass_d"] / 2, "y", s * (r_in + 1.0), s * (R_OUT + 1.0)))
        cuts.append(cyl_ax(5.5, "y", s * (r_in - 1.0), s * r_in))  # lamage plat (cale / bossage)
    for a in COL_ANGLES:
        x, y = col_xy(a)
        cuts.append(cylz(P["insert_d"] / 2, P["deck_z0"] - P["insert_depth"], P["deck_z0"] + 1, x, y))
    return body.cut(cuts)


# ---- Servos : repère local (x = longueur, y = largeur, z = hauteur/arbre) ----------------
def servo_local():
    L, W, H = P["sv_l"], P["sv_w"], P["sv_h"]
    sx, sy = P["sv_shaft_off"], W / 2
    e = P["sv_tab_ext"]
    body = box(0, L, 0, W, 0, H)
    tabs = box(-e, L + e, 0, W, P["sv_tab_z0"], P["sv_tab_z0"] + P["sv_tab_t"])
    gear = cylz(W / 2, H, H + P["sv_gear_h"], sx, sy)
    gear2 = cylz(2.8, H, H + P["sv_gear_h"] - 1.0, sx + 7.5, sy)
    spline = cylz(P["sv_spline_d"] / 2, H + P["sv_gear_h"], H + P["sv_gear_h"] + P["sv_spline_h"], sx, sy)
    cable = box(L, L + 2.0, W / 2 - 2.0, W / 2 + 2.0, 1.0, 4.0)
    s = fuse([body, tabs, gear, gear2, spline, cable])
    holes = [cylz(P["sv_tab_hole_d"] / 2, -1, H, L / 2 + k * P["sv_tab_hole_pitch"] / 2, sy) for k in (-1, 1)]
    return s.cut(holes)


def horn_plane_z():
    return P["sv_h"] + P["sv_gear_h"] + P["sv_spline_h"] + 0.5  # plan médian du palonnier


def horn_local():
    """Palonnier simple, orienté vers -x local (vers la biellette)."""
    W = P["sv_w"]
    sx, sy = P["sv_shaft_off"], W / 2
    zc = horn_plane_z()
    z0, z1 = zc - P["horn_t"] / 2, zc + P["horn_t"] / 2
    R = P["horn_r"]
    hub = cylz(P["horn_hub_d"] / 2, P["sv_h"] + P["sv_gear_h"] + 0.5, z1, sx, sy)
    pts = [V(sx, sy - 3.0, z0), V(sx - R, sy - 2.0, z0), V(sx - R, sy + 2.0, z0), V(sx, sy + 3.0, z0),
           V(sx, sy - 3.0, z0)]
    arm = Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, P["horn_t"]))
    tip = cylz(2.0, z0, z1, sx - R, sy)
    h = fuse([hub, arm, tip])
    return h.cut([cylz(P["sv_spline_d"] / 2, 0, P["sv_h"] + P["sv_gear_h"] + P["sv_spline_h"], sx, sy),
                  cylz(0.8, z0 - 1, z1 + 1, sx - R, sy)])


def servo_placements():
    """Placements des deux servos couchés sur le plateau (repère local -> global)."""
    W = P["sv_w"]
    zc = P["deck_z0"] + P["deck_t"]          # face supérieure du plateau
    y_bottom = P["rod_r"] - horn_plane_z()  # fond du servo X (arbre vers +Y)
    shaft_x = -P["horn_r"]
    # Servo X : x_loc -> -X, y_loc -> +Z, z_loc -> +Y
    rX = rot_from_axes(V(-1, 0, 0), V(0, 0, 1), V(0, 1, 0))
    oX = V(shaft_x + P["sv_shaft_off"], y_bottom, zc)
    # Servo Y : symétrique par rapport au plan x = y (x_loc -> -Y, y_loc -> -Z, z_loc -> +X)
    rY = rot_from_axes(V(0, -1, 0), V(0, 0, -1), V(1, 0, 0))
    oY = V(y_bottom, shaft_x + P["sv_shaft_off"], zc + W)
    return {"X": App.Placement(oX, rX), "Y": App.Placement(oY, rY)}


def shaft_center(which):
    pl = servo_placements()[which]
    return pl.multVec(V(P["sv_shaft_off"], P["sv_w"] / 2, horn_plane_z()))


def make_servo_deck():
    """Plateau servos : plaque, poteaux de fixation des pattes, colonnes supérieures."""
    z0, z1 = P["deck_z0"], P["deck_z0"] + P["deck_t"]
    parts = [cylz(R_OUT, z0, z1)]
    for a in COL_ANGLES:
        x, y = col_xy(a)
        parts.append(cylz(P["col_d"] / 2, z1 - 0.5, P["avio_z0"], x, y))
    # Poteaux sous les pattes de servo (repère local du servo)
    L, W, e = P["sv_l"], P["sv_w"], P["sv_tab_ext"]
    t0 = P["sv_tab_z0"]
    for pl in servo_placements().values():
        for (a, b) in ((-e, 0.0), (L, L + e)):
            parts.append(xform(box(a, b, 0, W, t0 - P["post_t"], t0), pl))
    body = fuse(parts).common(cylz(R_OUT, z0 - 1, P["avio_z0"] + 1))
    cuts = [cylz(P["deck_center_hole_d"] / 2, z0 - 1, z1 + 1)]
    for (x, y) in ((0, P["rod_r"]), (P["rod_r"], 0)):
        cuts.append(cylz(P["deck_rod_hole_d"] / 2, z0 - 1, z1 + 1, x, y))
    for a in COL_ANGLES:
        x, y = col_xy(a)
        cuts.append(cylz(P["m3_clear"] / 2, z0 - 1, P["avio_z0"] + 1, x, y))
    for pl in servo_placements().values():  # avant-trous M2 des pattes
        for k in (-1, 1):
            cx = L / 2 + k * P["sv_tab_hole_pitch"] / 2
            cuts.append(xform(cylz(P["post_pilot_d"] / 2, t0 - P["post_t"] - 1, t0 + 1, cx, W / 2), pl))
    return body.cut(cuts)


# ---- Électronique : positions sur le plateau avionique ---------------------------------
def avio_top():
    return P["avio_z0"] + P["avio_t"]


ESP_X0 = 13.0                          # ESP32-C3 en +X, USB-C vers l'extérieur
DIST_X0, DIST_X1 = -33.0, -13.0        # carte de distribution en -X
IMU_HOLES = [(-P["imu_hole_dx"], P["imu_hole_dy"]), (P["imu_hole_dx"], P["imu_hole_dy"])]


def dist_holes():
    w = P["dist_w"]
    return [(x, y) for x in (DIST_X0 + 2.5, DIST_X1 - 2.5) for y in (-w / 2 + 2.5, w / 2 - 2.5)]


def make_avionics_deck():
    z0, z1 = P["avio_z0"], avio_top()
    parts = [cylz(R_OUT, z0, z1)]
    for (x, y) in IMU_HOLES:
        parts.append(cylz(2.75, z1 - 0.5, z1 + P["imu_standoff"], x, y))
    for (x, y) in dist_holes():
        parts.append(cylz(2.5, z1 - 0.5, z1 + P["dist_standoff"], x, y))
    # Berceau ESP32-C3 (3 côtés, extrémité USB ouverte)
    x0, x1, hw = ESP_X0 - 1.6, ESP_X0 + P["esp_l"] - 3.0, P["esp_w"] / 2
    parts += [box(x0, x0 + 1.6, -hw - 1.8, hw + 1.8, z1 - 0.5, z1 + 3.0),
              box(x0, x1, hw + 0.2, hw + 1.8, z1 - 0.5, z1 + 3.0),
              box(x0, x1, -hw - 1.8, -hw - 0.2, z1 - 0.5, z1 + 3.0)]
    body = fuse(parts)
    cuts = []
    for a in COL_ANGLES:
        x, y = col_xy(a)
        cuts.append(cylz(P["m3_clear"] / 2, z0 - 1, z1 + 1, x, y))
    for (x, y) in IMU_HOLES:
        cuts.append(cylz(1.05, z0 + 1, z1 + P["imu_standoff"] + 1, x, y))   # M2.5 auto-taraudeuse
    for (x, y) in dist_holes():
        cuts.append(cylz(0.8, z0 + 1, z1 + P["dist_standoff"] + 1, x, y))   # M2 auto-taraudeuse
    for sy in (1, -1):  # passages de câbles servos
        cuts.append(box(-19.0, -9.0, sy * 27.0 - 2.5, sy * 27.0 + 2.5, z0 - 1, z1 + 1))
    cuts.append(cylz(4.0, z0 - 1, z1 + 1, 0, -8.0 - 6.0))  # passage de fils IMU
    return body.cut(cuts)


def make_top_plate():
    """Platine supérieure = interface banc (4x M4 sur Ø44 + Ø6.5 central)."""
    z0, z1 = P["top_z0"], P["top_z0"] + P["top_t"]
    parts = [cylz(R_OUT, z0, z1)]
    for a in COL_ANGLES:
        x, y = col_xy(a)
        parts.append(cylz(P["col_d"] / 2, avio_top(), z0 + 0.5, x, y))
    body = fuse(parts)
    cuts = [cylz(P["bench_center_d"] / 2, z0 - 1, z1 + 1)]
    for a in (0, 90, 180, 270):
        x, y = polar(P["bench_m4_r"], a)
        cuts.append(cylz(P["bench_m4_d"] / 2, z0 - 1, z1 + 1, x, y))
    for a in COL_ANGLES:
        x, y = col_xy(a)
        cuts.append(cylz(P["m3_clear"] / 2, avio_top() - 1, z1 + 1, x, y))
        cuts.append(cylz(P["m3_head_d"] / 2, z1 - P["m3_head_h"], z1 + 1, x, y))
    for a in (45.0, 135.0, 225.0, 315.0):  # allègements
        x, y = polar(22.0, a)
        cuts.append(cylz(6.0, z0 - 1, z1 + 1, x, y))
    return body.cut(cuts)


# --------------------------------------------------------------------------------------
# Composants achetés (représentation simplifiée)
# --------------------------------------------------------------------------------------
def make_motor():
    zt = P["motor_top_z"]
    return cylz(P["motor_d"] / 2, zt - P["motor_l"], zt)


def make_bearing(axis, r_in):
    s = 1 if r_in > 0 else -1
    a0, a1 = r_in, r_in + s * P["brg_w"]
    return cyl_ax(P["brg_od"] / 2, axis, a0, a1).cut(cyl_ax(P["brg_id"] / 2, axis, a0 - s, a1 + s))


def make_shim(axis, r_in):
    s = 1 if r_in > 0 else -1
    return cyl_ax(3.0, axis, r_in, r_in + s * P["shim_t"]).cut(
        cyl_ax(P["pin_d"] / 2, axis, r_in - s, r_in + s * (P["shim_t"] + 1)))


def make_pin(axis, r_bottom):
    s = 1 if r_bottom > 0 else -1
    return cyl_ax(P["pin_d"] / 2, axis, r_bottom, r_bottom + s * P["pin_l"])


def make_ball_stud(x, y):
    z1 = P["arm_z1"]
    return fuse([cylz(1.0, z1 - 5.0, z1, x, y), cylz(2.0, z1, z1 + 1.0, x, y),
                 Part.makeSphere(P["stud_ball_d"] / 2, V(x, y, P["ball_z"]))])


def make_m3_screw(x, y):
    z_head = P["top_z0"] + P["top_t"] - P["m3_head_h"]
    shank = cylz(1.5, z_head - 45.0, z_head, x, y)
    head = cylz(2.75, z_head, z_head + P["m3_head_h"], x, y)
    return fuse([shank, head])


def make_esp32():
    z = avio_top()
    x0, x1, hw = ESP_X0, ESP_X0 + P["esp_l"], P["esp_w"] / 2
    pcb = box(x0, x1, -hw, hw, z, z + P["esp_t"])
    usb = box(x1 - 7.5, x1 + 1.2, -4.5, 4.5, z + P["esp_t"], z + P["esp_t"] + 3.2)
    chip = box(x0 + 5.0, x0 + 10.0, -2.5, 2.5, z + P["esp_t"], z + P["esp_t"] + 0.9)
    ant = box(x0 + 0.5, x0 + 3.5, -6.0, 6.0, z + P["esp_t"], z + P["esp_t"] + 0.8)
    return fuse([pcb, usb, chip, ant])


def make_imu():
    z = avio_top() + P["imu_standoff"]
    hl, hw = P["imu_l"] / 2, P["imu_w"] / 2
    pcb = box(-hl, hl, -hw, hw, z, z + P["imu_t"])
    pcb = pcb.cut([cylz(1.5, z - 1, z + 3, x, y) for (x, y) in IMU_HOLES])
    chip = box(-2.0, 2.0, -2.0, 2.0, z + P["imu_t"], z + P["imu_t"] + 0.9)  # MPU6050 centré sur l'axe
    header = box(-10.2, 10.2, -hw + 0.3, -hw + 2.8, z + P["imu_t"], z + P["imu_t"] + 8.5)
    return fuse([pcb, chip, header])


def make_dist_board():
    z = avio_top() + P["dist_standoff"]
    hw = P["dist_w"] / 2
    pcb = box(DIST_X0, DIST_X1, -hw, hw, z, z + P["dist_t"])
    pcb = pcb.cut([cylz(1.1, z - 1, z + 3, x, y) for (x, y) in dist_holes()])
    zt = z + P["dist_t"]
    term = box(-30.0, -22.5, -5.0, 5.0, zt, zt + 10.0)              # bornier 5 V
    cap = cylz(3.15, zt, zt + 7.7, -18.0, 0.0)                        # 330 µF 10 V low-profile
    hdr = [box(-22.0, -14.4, s * 6.0 - 1.25, s * 6.0 + 1.25, zt, zt + 8.5) for s in (1, -1)]
    return fuse([pcb, term, cap] + hdr)


def make_pushrod(p_horn, p_ball):
    rod = cyl(0.8, p_horn, p_ball)
    link = Part.makeSphere(3.2, p_ball)       # chape à rotule M2
    clevis = Part.makeSphere(1.8, p_horn)     # Z-bend / chape côté palonnier
    return fuse([rod, link, clevis])


# --------------------------------------------------------------------------------------
# Cinématique
# --------------------------------------------------------------------------------------
def gimbal_placements(tx, ty):
    outer = App.Placement(V(), App.Rotation(V(0, 1, 0), ty))
    inner = outer.multiply(App.Placement(V(), App.Rotation(V(1, 0, 0), tx)))
    return outer, inner


def ball_points():
    return {"X": V(0, P["rod_r"], P["ball_z"]), "Y": V(P["rod_r"], 0, P["ball_z"])}


def horn_tip(which, phi):
    """Position du trou de palonnier pour un angle de servo phi (deg, + = vers le haut)."""
    c = shaft_center(which)
    R, a = P["horn_r"], math.radians(phi)
    if which == "X":
        return c + V(R * math.cos(a), 0, R * math.sin(a))
    return c + V(0, R * math.cos(a), R * math.sin(a))


def rod_length(which):
    return (horn_tip(which, 0.0) - ball_points()[which]).Length


def solve_servo(which, tx, ty):
    """Angle de servo (deg) qui donne la pose du cardan (tx, ty), par dichotomie."""
    _, inner = gimbal_placements(tx, ty)
    ball = inner.multVec(ball_points()[which])
    L = rod_length(which)
    lo, hi = -80.0, 80.0
    f = lambda p: (horn_tip(which, p) - ball).Length - L
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2, ball


# --------------------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------------------
class Item:
    def __init__(self, name, label, shape, group, color, kind):
        self.name, self.label, self.shape, self.group, self.color, self.kind = (
            name, label, shape, group, color, kind)


def build_items():
    """Pièces dans leur position neutre ; `group` indique quelle cinématique s'applique."""
    it = []
    add = lambda *a: it.append(Item(*a))
    add("motor_mount", "Support moteur (cardan interne)", make_motor_mount(), "inner", COLORS["print"], "print")
    add("gimbal_ring", "Bague de cardan (externe)", make_gimbal_ring(), "outer", COLORS["print2"], "print")
    add("frame", "Châssis inférieur", make_frame(), "static", COLORS["frame"], "print")
    add("servo_deck", "Plateau servos", make_servo_deck(), "static", COLORS["frame"], "print")
    add("avionics_deck", "Plateau avionique", make_avionics_deck(), "static", COLORS["frame"], "print")
    add("top_plate", "Platine banc", make_top_plate(), "static", COLORS["frame"], "print")
    add("motor_d9", "Moteur D9 factice", make_motor(), "inner", COLORS["motor"], "print")
    r_in, r_out = P["inner_boss_r"] + P["shim_t"], P["frame_ri"]
    for s, tag in ((1, "p"), (-1, "n")):
        add(f"bearing_x{tag}", "Roulement MR63ZZ", make_bearing("x", s * r_in), "outer", COLORS["steel"], "hw")
        add(f"shim_x{tag}", "Cale 3x6x0.5", make_shim("x", s * P["inner_boss_r"]), "inner", COLORS["steel"], "hw")
        add(f"pin_x{tag}", "Goupille 3x10", make_pin("x", s * (P["inner_boss_r"] - P["pin_depth"])), "inner",
            COLORS["steel"], "hw")
        add(f"bearing_y{tag}", "Roulement MR63ZZ", make_bearing("y", s * r_out), "static", COLORS["steel"], "hw")
        add(f"shim_y{tag}", "Cale 3x6x0.5", make_shim("y", s * P["outer_boss_r"]), "outer", COLORS["steel"], "hw")
        add(f"pin_y{tag}", "Goupille 3x10", make_pin("y", s * (P["outer_boss_r"] - P["pin_depth"])), "outer",
            COLORS["steel"], "hw")
    for which, pt in ball_points().items():
        add(f"ball_stud_{which}", "Rotule M2 (boule)", make_ball_stud(pt.x, pt.y), "inner", COLORS["steel"], "hw")
    sv, hn = servo_local(), horn_local()
    for which, pl in servo_placements().items():
        add(f"servo_{which}", "Servo MG90S", xform(sv, pl), "static", COLORS["servo"], "elec")
        add(f"horn_{which}", "Palonnier simple", hn, f"horn_{which}", COLORS["horn"], "hw")
        add(f"pushrod_{which}", "Biellette M2 + chapes", None, f"rod_{which}", COLORS["steel"], "hw")
    for i, a in enumerate(COL_ANGLES):
        x, y = col_xy(a)
        add(f"screw_m3_{i}", "Vis M3x45 DIN912", make_m3_screw(x, y), "static", COLORS["steel"], "hw")
    add("esp32c3", "ESP32-C3 Super Mini", make_esp32(), "static", COLORS["pcb_black"], "elec")
    add("mpu6050", "MPU6050 (GY-521)", make_imu(), "static", COLORS["pcb_blue"], "elec")
    add("dist_board", "Carte distribution 5 V", make_dist_board(), "static", COLORS["pcb_green"], "elec")
    return it


def pose(items, tx, ty):
    """Renvoie {nom: forme placée} et les angles de servo pour la pose (tx, ty)."""
    outer, inner = gimbal_placements(tx, ty)
    out, servo = {}, {}
    for which in ("X", "Y"):
        servo[which] = solve_servo(which, tx, ty)
    for i in items:
        if i.group == "static":
            out[i.name] = i.shape
        elif i.group == "outer":
            out[i.name] = xform(i.shape, outer)
        elif i.group == "inner":
            out[i.name] = xform(i.shape, inner)
        elif i.group.startswith("horn_"):
            w = i.group[-1]
            pl = servo_placements()[w]
            c_loc = V(P["sv_shaft_off"], P["sv_w"] / 2, 0)
            sign = -1 if w == "X" else 1
            out[i.name] = xform(xform(i.shape, rot_about(c_loc, V(0, 0, 1), sign * servo[w][0])), pl)
        elif i.group.startswith("rod_"):
            w = i.group[-1]
            phi, ball = servo[w]
            out[i.name] = make_pushrod(horn_tip(w, phi), ball)
    return out, {w: v[0] for w, v in servo.items()}


# --------------------------------------------------------------------------------------
# Vérifications
# --------------------------------------------------------------------------------------
# Contacts voulus (ajustements, pièces imbriquées)
ALLOWED = {
    ("horn_X", "pushrod_X"), ("horn_Y", "pushrod_Y"), ("ball_stud_X", "pushrod_X"), ("ball_stud_Y", "pushrod_Y"),
    ("horn_X", "servo_X"), ("horn_Y", "servo_Y"),
    ("ball_stud_X", "motor_mount"), ("ball_stud_Y", "motor_mount"),  # filetage M2 dans le bras
}


def bb_overlap(a, b, tol=0.0):
    A, B = a.BoundBox, b.BoundBox
    return not (A.XMax < B.XMin - tol or B.XMax < A.XMin - tol or A.YMax < B.YMin - tol or
                B.YMax < A.YMin - tol or A.ZMax < B.ZMin - tol or B.ZMax < A.ZMin - tol)


def interferences(shapes, only=None, tol_vol=1e-3):
    names = sorted(shapes)
    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in ALLOWED or (b, a) in ALLOWED:
                continue
            if only and a not in only and b not in only:
                continue
            sa, sb = shapes[a], shapes[b]
            if not bb_overlap(sa, sb):
                continue
            v = sa.common(sb).Volume
            if v > tol_vol:
                hits.append((a, b, v))
    return hits


def min_gap(a, b):
    return a.distToShape(b)[0]


def run_checks(items, log):
    ok = True
    static = {i.name for i in items if i.group == "static"}
    m = P["max_tilt"]
    poses = [(0, 0)] + [(sx * m, sy * m) for sx in (-1, 0, 1) for sy in (-1, 0, 1) if (sx, sy) != (0, 0)]
    for (tx, ty) in poses:
        shapes, _ = pose(items, tx, ty)
        moving = None if (tx, ty) == (0, 0) else {n for n in shapes if n not in static}
        hits = interferences(shapes, only=moving)
        status = "OK" if not hits else "INTERFÉRENCES"
        log(f"  pose θx={tx:+5.1f}° θy={ty:+5.1f}° : {status}")
        for a, b, v in hits:
            ok = False
            log(f"      {a} <-> {b} : {v:.3f} mm³")
    # Jeux minimum entre partie mobile et fixe, sur les 4 coins du débattement combiné
    corners = [pose(items, sx * m, sy * m)[0] for sx in (-1, 1) for sy in (-1, 1)]
    for a, b in (("motor_mount", "servo_deck"), ("motor_mount", "frame"), ("gimbal_ring", "frame"),
                 ("pushrod_X", "servo_deck"), ("pushrod_Y", "servo_deck"), ("motor_mount", "gimbal_ring"),
                 ("motor_d9", "frame")):
        g = min(min_gap(sh[a], sh[b]) for sh in corners)
        log(f"  jeu mini {a} / {b} (coins ±{m:.0f}°/±{m:.0f}°) : {g:.2f} mm")
    return ok


# --------------------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------------------
def main():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    out_dir = os.environ.get("TVC_OUT", os.path.join(here, "exports"))
    tx = float(os.environ.get("TVC_THETA_X", "0"))
    ty = float(os.environ.get("TVC_THETA_Y", "0"))
    lines = []

    def log(s=""):
        lines.append(s)
        print(s)

    items = build_items()
    for i in items:
        if i.shape is not None and not i.shape.isValid():
            log(f"!! forme invalide : {i.name}")

    log("== Cinématique (levier bras {:.0f} mm / palonnier {:.0f} mm = {:.2f}:1)".format(
        P["rod_r"], P["horn_r"], P["rod_r"] / P["horn_r"]))
    log("  longueur biellettes entre-axes : X = {:.1f} mm, Y = {:.1f} mm".format(rod_length("X"), rod_length("Y")))
    for t in (-P["max_tilt"], -5.0, -1.0, 1.0, 5.0, P["max_tilt"]):
        log("  θx={:+5.1f}° -> servo X {:+6.2f}°   |   θy={:+5.1f}° -> servo Y {:+6.2f}°".format(
            t, solve_servo("X", t, 0)[0], t, solve_servo("Y", 0, t)[0]))
    log("  couplage : θx=+10°, θy=+10° -> servo X {:+.2f}°, servo Y {:+.2f}°".format(
        solve_servo("X", 10, 10)[0], solve_servo("Y", 10, 10)[0]))

    if os.environ.get("TVC_CHECK", "1") != "0":
        log("== Interférences (débattement ±{:.0f}° sur chaque axe)".format(P["max_tilt"]))
        run_checks(items, log)

    shapes, servo = pose(items, tx, ty)
    log("== Pose exportée : θx={:+.1f}°, θy={:+.1f}° (servo X {:+.2f}°, servo Y {:+.2f}°)".format(
        tx, ty, servo["X"], servo["Y"]))

    log("== Pièces imprimées (volume matière)")
    for i in items:
        if i.kind == "print":
            v = i.shape.Volume
            log("  {:<16s} {:7.1f} cm³  ~{:5.1f} g PETG plein  bbox {:.1f} x {:.1f} x {:.1f}".format(
                i.name, v / 1000, v / 1000 * 1.27, i.shape.BoundBox.XLength, i.shape.BoundBox.YLength,
                i.shape.BoundBox.ZLength))

    # Document FreeCAD
    doc = App.newDocument("TVC_Module")
    groups = {}
    for k, lbl in (("print", "Pieces_imprimees"), ("hw", "Quincaillerie"), ("elec", "Electronique")):
        groups[k] = doc.addObject("App::DocumentObjectGroup", lbl)
    objs = []
    for i in items:
        o = doc.addObject("Part::Feature", i.name)
        o.Label = i.name
        o.Shape = shapes[i.name]
        groups[i.kind].addObject(o)
        if App.GuiUp:
            o.ViewObject.ShapeColor = i.color
        objs.append(o)
    doc.recompute()

    if os.environ.get("TVC_EXPORT", "1") != "0":
        import Import
        os.makedirs(os.path.join(out_dir, "stl"), exist_ok=True)
        App.ParamGet("User parameter:BaseApp/Preferences/Document").SetInt("CountBackupFiles", 0)
        doc.saveAs(os.path.join(out_dir, "tvc_module.FCStd"))
        Import.export(objs, os.path.join(out_dir, "tvc_module_assembly.step"))
        neutral, _ = pose(items, 0, 0)
        import MeshPart
        for i in items:
            if i.kind == "print":
                mesh = MeshPart.meshFromShape(Shape=neutral[i.name], LinearDeflection=0.02,
                                              AngularDeflection=0.25, Relative=False)
                mesh.write(os.path.join(out_dir, "stl", i.name + ".stl"))
        with open(os.path.join(out_dir, "report.txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        log(f"== Exports écrits dans {out_dir}")
    return doc


TVC_DOC = main()
