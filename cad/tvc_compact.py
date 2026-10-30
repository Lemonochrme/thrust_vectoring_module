# -*- coding: utf-8 -*-
"""
Module TVC compact pour tube de 4 cm (Ø intérieur 38 mm) - moteur D9 factice.

Script FreeCAD (atelier Part), paramétrique, autonome.

Différences avec tvc_module.py (version Ø76) :
  - pivot = mini-joint de cardan du commerce placé au-dessus du moteur, le moteur est suspendu
  - servos MG90S empilés l'un au-dessus de l'autre, arbre radial
  - électronique sur un support vertical au-dessus des servos
  - le diamètre est limité, pas la longueur

Utilisation :
  freecadcmd cad/tvc_compact.py
  TVC_THETA_X / TVC_THETA_Y, TVC_OUT, TVC_CHECK=0, TVC_EXPORT=0 : comme tvc_module.py

Repère : Z vers l'avant (buse vers -Z), origine au centre du joint de cardan. Unités : mm, degrés.
"""
import math
import os

import FreeCAD as App
import Part

V = App.Vector

P = dict(
    # Tube de la fusée (référence d'encombrement)
    tube_id=38.0, tube_od=40.0, tube_z0=-15.0,
    mod_r=18.8, shell_t=1.4,
    # Moteur D9 factice
    motor_d=24.0, motor_l=70.0, motor_top_z=-20.0,
    # Support moteur
    mm_bore=24.4, mm_wall=1.5, mm_bottom_z=-54.0, mm_cap_top=-15.0, mm_boss_d=10.0, mm_boss_top=-12.5,
    set_screw_z=-48.0,
    # Mini-joint de cardan (commerce) : Ø9, alésages Ø3, moyeux de 7 mm
    uj_d=9.0, uj_hub_l=7.0, uj_half=4.5,
    shaft_d=3.0, shaft_low_z=(-19.0, -5.0), shaft_up_z=(5.0, 19.0),
    # Rotules sur le support moteur
    attach_r=12.0, attach_boss_d=5.0, stud_ball_d=4.8,
    # Corps de baie (plancher + coque + platines servos)
    bay_z0=12.0, floor_t=6.0, bay_z1=128.0, floor_hole_d=10.0,
    # Servo MG90S
    sv_l=22.8, sv_w=12.2, sv_h=22.5, sv_tab_ext=4.85, sv_tab_z0=15.7, sv_tab_t=2.5,
    sv_tab_hole_d=2.0, sv_tab_hole_pitch=27.5, sv_shaft_off=6.0,
    sv_gear_h=4.0, sv_spline_d=4.8, sv_spline_h=3.0,
    horn_r=7.0, horn_hub_d=7.0, horn_t=2.0,
    sv_bottom_r=15.5,              # distance axe -> fond du servo
    sv_low_z0=24.0, sv_high_z0=60.0,
    plate_t=3.0, pilot_d=1.6,
    # Avionique
    sled_z0=90.0, sled_z1=124.0, sled_t=2.0,
    esp_l=22.5, esp_w=18.0, esp_t=1.0, imu_l=21.0, imu_w=16.0, imu_t=1.6, dist_l=26.0, dist_w=14.0,
    dist_t=1.6,
    # Platine supérieure / banc
    top_t=4.0, spigot_h=4.0, bench_hole_r=13.0, bench_insert_d=4.0,
    # Débattement
    max_tilt=10.0,
)
R_OUT = P["mod_r"]
R_IN = R_OUT - P["shell_t"]

COLORS = {
    "print": (0.95, 0.55, 0.10), "frame": (0.25, 0.25, 0.28), "motor": (0.85, 0.80, 0.70),
    "servo": (0.10, 0.25, 0.70), "horn": (0.95, 0.95, 0.95), "steel": (0.75, 0.76, 0.78),
    "uj": (0.55, 0.57, 0.60), "pcb_blue": (0.10, 0.30, 0.65), "pcb_black": (0.08, 0.08, 0.08),
    "pcb_green": (0.10, 0.45, 0.20), "tube": (0.80, 0.85, 0.95),
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
    m = App.Matrix(ex.x, ey.x, ez.x, 0, ex.y, ey.y, ez.y, 0, ex.z, ey.z, ez.z, 0, 0, 0, 0, 1)
    return App.Rotation(m)


def polar(r, deg):
    return math.cos(math.radians(deg)) * r, math.sin(math.radians(deg)) * r


def clip(shape, z0, z1, r=R_OUT):
    return shape.common(cylz(r, z0, z1))


# --------------------------------------------------------------------------------------
# Servos : repère local (x = longueur, y = largeur, z = hauteur/arbre)
# --------------------------------------------------------------------------------------
def horn_plane_z():
    return P["sv_h"] + P["sv_gear_h"] + P["sv_spline_h"] + 0.5


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


def horn_local():
    """Palonnier simple orienté vers -x local."""
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


# Servo "X" (bas) : arbre vers +Y, palonnier vers -X  -> agit surtout sur la rotation autour de X
# Servo "Y" (haut): arbre vers +X, palonnier vers -Y  -> agit surtout sur la rotation autour de Y
# (base, signe) : orientation du palonnier dans le repère local = base + signe * phi
SERVOS = {
    "X": dict(ex=V(0, 0, 1), ez=V(0, 1, 0), base=90.0, sign=1.0, z0_key="sv_low_z0"),
    "Y": dict(ex=V(0, 0, 1), ez=V(1, 0, 0), base=-90.0, sign=-1.0, z0_key="sv_high_z0"),
}


def servo_placement(which):
    s = SERVOS[which]
    ex, ez = s["ex"], s["ez"]
    ey = ez.cross(ex)
    W = P["sv_w"]
    # origine locale : fond du servo à sv_bottom_r de l'axe, centré en largeur
    o = ez * (-P["sv_bottom_r"]) - ey * (W / 2) + V(0, 0, P[s["z0_key"]])
    return App.Placement(o, rot_from_axes(ex, ey, ez))


def horn_dir_local(which, phi):
    s = SERVOS[which]
    a = math.radians(s["base"] + s["sign"] * phi)
    return -math.cos(a), -math.sin(a)


def horn_tip(which, phi):
    dx, dy = horn_dir_local(which, phi)
    R = P["horn_r"]
    loc = V(P["sv_shaft_off"] + R * dx, P["sv_w"] / 2 + R * dy, horn_plane_z())
    return servo_placement(which).multVec(loc)


def ball_point(which):
    t = horn_tip(which, 0.0)
    a = math.atan2(t.y, t.x)
    r = P["attach_r"]
    return V(r * math.cos(a), r * math.sin(a), P["mm_boss_top"] + 1.0 + P["stud_ball_d"] / 2)


# --------------------------------------------------------------------------------------
# Pièces imprimées
# --------------------------------------------------------------------------------------
def make_motor_mount():
    ro = P["mm_bore"] / 2 + P["mm_wall"]
    parts = [cylz(ro, P["mm_bottom_z"], P["mm_cap_top"]),
             cylz(P["mm_boss_d"] / 2, P["mm_cap_top"] - 1, P["mm_boss_top"])]
    for w in ("X", "Y"):
        b = ball_point(w)
        parts.append(cylz(P["attach_boss_d"] / 2, P["mm_cap_top"] - 3.0, P["mm_boss_top"], b.x, b.y))
        # nervure entre bossage et tube
        a = math.atan2(b.y, b.x)
        rib = box(0, P["attach_r"], -1.5, 1.5, P["mm_cap_top"] - 3.0, P["mm_boss_top"])
        parts.append(xform(rib, App.Placement(V(), App.Rotation(V(0, 0, 1), math.degrees(a)))))
    parts.append(cyl(3.5, V(0, -(ro - 1), P["set_screw_z"]), V(0, -(ro + 2.5), P["set_screw_z"])))
    body = fuse(parts)
    cuts = [cylz(P["mm_bore"] / 2, P["mm_bottom_z"] - 1, P["motor_top_z"]),
            cylz(P["shaft_d"] / 2, P["shaft_low_z"][0], P["mm_boss_top"] + 1)]
    for w in ("X", "Y"):
        b = ball_point(w)
        cuts.append(cylz(0.9, P["mm_cap_top"] - 4, P["mm_boss_top"] + 1, b.x, b.y))
    cuts.append(cyl(1.25, V(0, -(ro - 2), P["set_screw_z"]), V(0, -(ro + 3.5), P["set_screw_z"])))
    return body.cut(cuts)


def rod_xy_at(which, z):
    a, b = horn_tip(which, 0.0), ball_point(which)
    t = (z - b.z) / (a.z - b.z)
    return b.x + t * (a.x - b.x), b.y + t * (a.y - b.y)


def make_bay():
    """Corps de baie : plancher porte-cardan, coque, platines des deux servos."""
    z0, zf, z1 = P["bay_z0"], P["bay_z0"] + P["floor_t"], P["bay_z1"]
    parts = [cylz(R_OUT, z0, zf), ring(R_IN, R_OUT, zf - 0.5, z1)]
    L, W, e, t0 = P["sv_l"], P["sv_w"], P["sv_tab_ext"], P["sv_tab_z0"]
    windows = []
    for w in ("X", "Y"):
        pl = servo_placement(w)
        # platine sous les pattes, sur toute la corde
        plate = xform(box(-e - 1.5, L + e + 1.5, -30, 30, t0 - P["plate_t"], t0), pl)
        parts.append(clip(plate, zf - 0.5, z1))
        windows.append(xform(box(-0.3, L + 0.3, -0.2, W + 0.2, t0 - P["plate_t"] - 1, t0 + 1), pl))
    body = fuse(parts)
    cuts = list(windows)
    cuts.append(cylz(P["shaft_d"] / 2, z0 - 1, P["shaft_up_z"][1]))
    zm = (z0 + zf) / 2
    for w in ("X", "Y"):
        x, y = rod_xy_at(w, zm)
        cuts.append(cylz(P["floor_hole_d"] / 2, z0 - 1, zf + 1, x, y))
        pl = servo_placement(w)
        for k in (-1, 1):  # avant-trous M2 des pattes
            cx = L / 2 + k * P["sv_tab_hole_pitch"] / 2
            cuts.append(xform(cylz(P["pilot_d"] / 2, t0 - P["plate_t"] - 1, t0 + 1, cx, W / 2), pl))
        # fenêtre dans la coque devant le palonnier (accès, débattement)
        c = horn_tip(w, 0.0)
        s = servo_placement(w).Rotation.multVec(V(0, 0, 1))  # direction de l'arbre
        win = box(-10, 10, -12, 12, -12, 12)
        ang = math.degrees(math.atan2(s.y, s.x))
        win = xform(win, App.Placement(V(), App.Rotation(V(0, 0, 1), ang)))
        cuts.append(xform(win, App.Placement(V(s.x * 22, s.y * 22, c.z), App.Rotation())))
    # fenêtres d'accès électronique (USB, câbles)
    for a in (45.0, 225.0):
        x, y = polar(R_OUT, a)
        cuts.append(xform(box(-4, 4, -8, 8, 96, 116), App.Placement(V(x, y, 0), App.Rotation(V(0, 0, 1), a))))
    # vis radiales M2 de la platine supérieure
    for a in (0.0, 120.0, 240.0):
        x, y = polar(R_OUT + 1, a)
        cuts.append(cyl(1.1, V(0, 0, z1 - 2.0) * 0 + V(x, y, z1 - 2.0), V(x * 0.8, y * 0.8, z1 - 2.0)))
    return body.cut(cuts)


def make_top():
    """Platine supérieure (interface banc) + support d'électronique."""
    z1 = P["bay_z1"]
    zt = z1 + P["top_t"]
    parts = [cylz(R_OUT, z1, zt), ring(R_IN - 2.0, R_IN - 0.1, z1 - P["spigot_h"], z1 + 0.5)]
    hw = P["sled_t"] / 2
    parts.append(clip(box(-16.5, 16.5, -hw, hw, P["sled_z0"], z1 + 0.5), P["sled_z0"], z1 + 1, R_IN - 0.1))
    body = fuse(parts)
    cuts = [box(-6.5, 6.5, 0.3, 7.3, z1 - P["spigot_h"] - 1, zt + 1)]  # passage USB-C
    for a in (45.0, 135.0, 225.0, 315.0):
        x, y = polar(P["bench_hole_r"], a)
        cuts.append(cylz(P["bench_insert_d"] / 2, zt - 6.0, zt + 1, x, y))
    for a in (0.0, 120.0, 240.0):
        x, y = polar(R_OUT + 1, a)
        cuts.append(cyl(0.8, V(x, y, z1 - 2.0), V(x * 0.7, y * 0.7, z1 - 2.0)))
    for (x, z) in esp_holes() + imu_holes() + dist_holes():
        cuts.append(cyl(0.8, V(x, -hw - 1, z), V(x, hw + 1, z)))
    return body.cut(cuts)


# --------------------------------------------------------------------------------------
# Électronique (sur le support vertical, plan XZ)
# --------------------------------------------------------------------------------------
ESP_Z0 = 99.5
IMU_Z0, DIST_Z0 = 107.0, 91.0


def esp_holes():
    return []


def imu_holes():
    return [(-7.5, IMU_Z0 + P["imu_w"] - 3.0), (7.5, IMU_Z0 + P["imu_w"] - 3.0)]


def dist_holes():
    x = P["dist_l"] / 2 - 2.5
    return [(-x, DIST_Z0 + 2.5), (x, DIST_Z0 + 2.5), (-x, DIST_Z0 + P["dist_w"] - 2.5),
            (x, DIST_Z0 + P["dist_w"] - 2.5)]


def make_esp32():
    y0 = P["sled_t"] / 2
    hw = P["esp_w"] / 2
    z0, z1 = ESP_Z0, ESP_Z0 + P["esp_l"]
    t = P["esp_t"]
    pcb = box(-hw, hw, y0, y0 + t, z0, z1)
    usb = box(-4.5, 4.5, y0 + t, y0 + t + 3.2, z1 - 7.5, z1 + 1.2)
    chip = box(-2.5, 2.5, y0 + t, y0 + t + 0.9, z0 + 8, z0 + 13)
    return fuse([pcb, usb, chip])


def make_imu():
    y0 = -P["sled_t"] / 2 - 2.0   # sur entretoises de 2 mm
    hl = P["imu_l"] / 2
    z0, z1 = IMU_Z0, IMU_Z0 + P["imu_w"]
    pcb = box(-hl, hl, y0 - P["imu_t"], y0, z0, z1)
    pcb = pcb.cut([cyl(1.5, V(x, y0 - 3, z), V(x, y0 + 1, z)) for (x, z) in imu_holes()])
    chip = box(-2, 2, y0 - P["imu_t"] - 0.9, y0 - P["imu_t"], (z0 + z1) / 2 - 2, (z0 + z1) / 2 + 2)
    header = box(-10.2, 10.2, y0 - P["imu_t"] - 2.5, y0 - P["imu_t"], z0 + 0.3, z0 + 2.8)
    spacers = [cyl(2.0, V(x, -P["sled_t"] / 2, z), V(x, y0, z)) for (x, z) in imu_holes()]
    return fuse([pcb, chip, header] + spacers)


def make_dist_board():
    y0 = -P["sled_t"] / 2 - 2.0
    hl = P["dist_l"] / 2
    z0, z1 = DIST_Z0, DIST_Z0 + P["dist_w"]
    t = P["dist_t"]
    pcb = box(-hl, hl, y0 - t, y0, z0, z1)
    pcb = pcb.cut([cyl(1.1, V(x, y0 - 3, z), V(x, y0 + 1, z)) for (x, z) in dist_holes()])
    yt = y0 - t
    term = box(-10.0, -0.5, yt - 8.5, yt, z0 + 3.0, z0 + 10.5)          # bornier 5 V
    cap = cyl(3.15, V(4.0, yt, z0 + 7.0), V(4.0, yt - 7.7, z0 + 7.0))    # 330 µF
    hdr = box(8.0, 10.5, yt - 8.5, yt, z0 + 2.0, z0 + 12.0)              # 2 x 3 broches
    spacers = [cyl(2.0, V(x, -P["sled_t"] / 2, z), V(x, y0, z)) for (x, z) in dist_holes()]
    return fuse([pcb, term, cap, hdr] + spacers)


# --------------------------------------------------------------------------------------
# Composants achetés
# --------------------------------------------------------------------------------------
def make_motor():
    zt = P["motor_top_z"]
    return cylz(P["motor_d"] / 2, zt - P["motor_l"], zt)


def make_uj_lower():
    """Moyeu inférieur + chape (axe X), solidaire du moteur."""
    r, h = P["uj_d"] / 2, P["uj_half"]
    hub = cylz(r, -h - P["uj_hub_l"], -h + 1.0)
    ears = [box(s * 3.0 if s > 0 else -r, r if s > 0 else -3.0, -2.2, 2.2, -h + 0.5, 2.0) for s in (1, -1)]
    ears = [e.common(cylz(r, -h, 2.5)) for e in ears]
    s = fuse([hub] + ears)
    return s.cut([cylz(P["shaft_d"] / 2, -h - P["uj_hub_l"] - 1, -h - 1.0),
                  cyl(0.75, V(-r - 1, 0, 0), V(r + 1, 0, 0))])


def make_uj_cross():
    c = box(-1.9, 1.9, -1.9, 1.9, -1.9, 1.9)
    px = cyl(0.75, V(-4.4, 0, 0), V(4.4, 0, 0))
    py = cyl(0.75, V(0, -4.4, 0), V(0, 4.4, 0))
    return fuse([c, px, py])


def make_uj_upper():
    """Moyeu supérieur + chape (axe Y), fixe."""
    r, h = P["uj_d"] / 2, P["uj_half"]
    hub = cylz(r, h - 1.0, h + P["uj_hub_l"])
    ears = [box(-2.2, 2.2, 3.0 if s > 0 else -r, r if s > 0 else -3.0, -2.0, h - 0.5) for s in (1, -1)]
    ears = [e.common(cylz(r, -2.5, h)) for e in ears]
    s = fuse([hub] + ears)
    return s.cut([cylz(P["shaft_d"] / 2, h + 1.0, h + P["uj_hub_l"] + 1),
                  cyl(0.75, V(0, -r - 1, 0), V(0, r + 1, 0))])


def make_shaft(z0, z1):
    return cylz(P["shaft_d"] / 2, z0, z1)


def make_ball_stud(b):
    top = P["mm_boss_top"]
    return fuse([cylz(1.0, top - 4.0, top, b.x, b.y), cylz(2.0, top, top + 1.0, b.x, b.y),
                 Part.makeSphere(P["stud_ball_d"] / 2, b)])


def make_pushrod(p_horn, p_ball):
    return fuse([cyl(0.8, p_horn, p_ball), Part.makeSphere(3.2, p_ball), Part.makeSphere(1.8, p_horn)])


def make_tube():
    return ring(P["tube_id"] / 2, P["tube_od"] / 2, P["tube_z0"], P["bay_z1"] + P["top_t"])


# --------------------------------------------------------------------------------------
# Cinématique
# --------------------------------------------------------------------------------------
def gimbal_placements(tx, ty):
    outer = App.Placement(V(), App.Rotation(V(0, 1, 0), ty))
    inner = outer.multiply(App.Placement(V(), App.Rotation(V(1, 0, 0), tx)))
    return outer, inner


def rod_length(which):
    return (horn_tip(which, 0.0) - ball_point(which)).Length


def solve_servo(which, tx, ty):
    _, inner = gimbal_placements(tx, ty)
    ball = inner.multVec(ball_point(which))
    L = rod_length(which)
    f = lambda p: (horn_tip(which, p) - ball).Length - L
    lo, hi = -80.0, 80.0
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
    it = []
    add = lambda *a: it.append(Item(*a))
    add("motor_mount", "Support moteur", make_motor_mount(), "inner", COLORS["print"], "print")
    add("bay", "Corps de baie (plancher, coque, platines servos)", make_bay(), "static", COLORS["frame"], "print")
    add("top", "Platine banc + support électronique", make_top(), "static", COLORS["frame"], "print")
    add("motor_d9", "Moteur D9 factice", make_motor(), "inner", COLORS["motor"], "print")
    add("uj_lower", "Joint de cardan - moyeu bas", make_uj_lower(), "inner", COLORS["uj"], "hw")
    add("uj_cross", "Joint de cardan - croisillon", make_uj_cross(), "outer", COLORS["uj"], "hw")
    add("uj_upper", "Joint de cardan - moyeu haut", make_uj_upper(), "static", COLORS["uj"], "hw")
    add("shaft_low", "Goupille 3x14", make_shaft(*P["shaft_low_z"]), "inner", COLORS["steel"], "hw")
    add("shaft_up", "Goupille 3x14", make_shaft(*P["shaft_up_z"]), "static", COLORS["steel"], "hw")
    sv, hn = servo_local(), horn_local()
    for w in ("X", "Y"):
        add(f"ball_stud_{w}", "Rotule M2 (boule)", make_ball_stud(ball_point(w)), "inner", COLORS["steel"], "hw")
        add(f"servo_{w}", "Servo MG90S", xform(sv, servo_placement(w)), "static", COLORS["servo"], "elec")
        add(f"horn_{w}", "Palonnier simple", hn, f"horn_{w}", COLORS["horn"], "hw")
        add(f"pushrod_{w}", "Biellette M2 + chape", None, f"rod_{w}", COLORS["steel"], "hw")
    add("esp32c3", "ESP32-C3 Super Mini", make_esp32(), "static", COLORS["pcb_black"], "elec")
    add("mpu6050", "MPU6050 (GY-521)", make_imu(), "static", COLORS["pcb_blue"], "elec")
    add("dist_board", "Carte distribution 5 V", make_dist_board(), "static", COLORS["pcb_green"], "elec")
    add("tube_ref", "Tube de fusée Ø38/40 (référence)", make_tube(), "static", COLORS["tube"], "ref")
    return it


def pose(items, tx, ty):
    outer, inner = gimbal_placements(tx, ty)
    servo = {w: solve_servo(w, tx, ty) for w in ("X", "Y")}
    out = {}
    for i in items:
        if i.group == "static":
            out[i.name] = i.shape
        elif i.group == "outer":
            out[i.name] = xform(i.shape, outer)
        elif i.group == "inner":
            out[i.name] = xform(i.shape, inner)
        elif i.group.startswith("horn_"):
            w = i.group[-1]
            s = SERVOS[w]
            c = V(P["sv_shaft_off"], P["sv_w"] / 2, 0)
            local = xform(i.shape, rot_about(c, V(0, 0, 1), s["base"] + s["sign"] * servo[w][0]))
            out[i.name] = xform(local, servo_placement(w))
        elif i.group.startswith("rod_"):
            w = i.group[-1]
            phi, ball = servo[w]
            out[i.name] = make_pushrod(horn_tip(w, phi), ball)
    return out, {w: v[0] for w, v in servo.items()}


# --------------------------------------------------------------------------------------
# Vérifications
# --------------------------------------------------------------------------------------
ALLOWED = {
    ("horn_X", "pushrod_X"), ("horn_Y", "pushrod_Y"), ("ball_stud_X", "pushrod_X"), ("ball_stud_Y", "pushrod_Y"),
    ("horn_X", "servo_X"), ("horn_Y", "servo_Y"),
    ("ball_stud_X", "motor_mount"), ("ball_stud_Y", "motor_mount"),        # filetage M2
    ("uj_lower", "uj_cross"), ("uj_upper", "uj_cross"),                    # axes du croisillon
    ("uj_lower", "shaft_low"), ("uj_upper", "shaft_up"),                   # vis de pression
}


def bb_overlap(a, b):
    A, B = a.BoundBox, b.BoundBox
    return not (A.XMax < B.XMin or B.XMax < A.XMin or A.YMax < B.YMin or B.YMax < A.YMin or
                A.ZMax < B.ZMin or B.ZMax < A.ZMin)


def interferences(shapes, only=None, tol_vol=1e-3):
    names = sorted(shapes)
    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in ALLOWED or (b, a) in ALLOWED:
                continue
            if only and a not in only and b not in only:
                continue
            if not bb_overlap(shapes[a], shapes[b]):
                continue
            v = shapes[a].common(shapes[b]).Volume
            if v > tol_vol:
                hits.append((a, b, v))
    return hits


def run_checks(items, log):
    ok = True
    static = {i.name for i in items if i.group == "static"}
    m = P["max_tilt"]
    poses = [(0, 0)] + [(sx * m, sy * m) for sx in (-1, 0, 1) for sy in (-1, 0, 1) if (sx, sy) != (0, 0)]
    for (tx, ty) in poses:
        shapes, _ = pose(items, tx, ty)
        moving = None if (tx, ty) == (0, 0) else {n for n in shapes if n not in static}
        hits = interferences(shapes, only=moving)
        log(f"  pose θx={tx:+5.1f}° θy={ty:+5.1f}° : {'OK' if not hits else 'INTERFÉRENCES'}")
        for a, b, v in hits:
            ok = False
            log(f"      {a} <-> {b} : {v:.3f} mm³")
    corners = [pose(items, sx * m, sy * m)[0] for sx in (-1, 1) for sy in (-1, 1)]
    for a, b in (("motor_mount", "tube_ref"), ("motor_mount", "bay"), ("pushrod_X", "bay"),
                 ("pushrod_Y", "bay"), ("pushrod_X", "servo_X"), ("pushrod_Y", "servo_X"),
                 ("uj_lower", "uj_upper"), ("motor_mount", "uj_upper")):
        g = min(sh[a].distToShape(sh[b])[0] for sh in corners)
        log(f"  jeu mini {a} / {b} (coins ±{m:.0f}°/±{m:.0f}°) : {g:.2f} mm")
    return ok


# --------------------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------------------
RENDER_HIDE = ["tube_ref"]


def main():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    out_dir = os.environ.get("TVC_OUT", os.path.join(here, "exports_compact"))
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

    log("== Cinématique (palonnier {:.0f} mm, rotules à {:.0f} mm de l'axe)".format(P["horn_r"], P["attach_r"]))
    log("  longueur biellettes entre-axes : X = {:.1f} mm, Y = {:.1f} mm".format(rod_length("X"), rod_length("Y")))
    for t in (-P["max_tilt"], -5.0, -1.0, 1.0, 5.0, P["max_tilt"]):
        log("  θx={:+5.1f}° -> servo X {:+6.2f}° Y {:+6.2f}°   |   θy={:+5.1f}° -> servo X {:+6.2f}° Y {:+6.2f}°".format(
            t, solve_servo("X", t, 0)[0], solve_servo("Y", t, 0)[0],
            t, solve_servo("X", 0, t)[0], solve_servo("Y", 0, t)[0]))

    if os.environ.get("TVC_CHECK", "1") != "0":
        log("== Interférences (débattement ±{:.0f}° sur chaque axe)".format(P["max_tilt"]))
        run_checks(items, log)

    shapes, servo = pose(items, tx, ty)
    log("== Pose exportée : θx={:+.1f}°, θy={:+.1f}° (servo X {:+.2f}°, servo Y {:+.2f}°)".format(
        tx, ty, servo["X"], servo["Y"]))
    zmin = min(s.BoundBox.ZMin for n, s in shapes.items() if n != "tube_ref")
    zmax = max(s.BoundBox.ZMax for n, s in shapes.items() if n != "tube_ref")
    rmax = max(max(abs(s.BoundBox.XMin), abs(s.BoundBox.XMax), abs(s.BoundBox.YMin), abs(s.BoundBox.YMax))
               for n, s in shapes.items() if n not in ("tube_ref", "motor_d9", "motor_mount"))
    log("== Encombrement : longueur {:.0f} mm (buse -> platine), boîte englobante hors moteur ±{:.1f} mm".format(
        zmax - zmin, rmax))

    log("== Pièces imprimées (volume matière)")
    for i in items:
        if i.kind == "print":
            v = i.shape.Volume
            bb = i.shape.BoundBox
            log("  {:<12s} {:6.1f} cm³  ~{:5.1f} g PETG plein  bbox {:.1f} x {:.1f} x {:.1f}".format(
                i.name, v / 1000, v / 1000 * 1.27, bb.XLength, bb.YLength, bb.ZLength))

    doc = App.newDocument("TVC_Compact")
    groups = {}
    for k, lbl in (("print", "Pieces_imprimees"), ("hw", "Quincaillerie"), ("elec", "Electronique"),
                   ("ref", "Reference")):
        groups[k] = doc.addObject("App::DocumentObjectGroup", lbl)
    objs = []
    for i in items:
        o = doc.addObject("Part::Feature", i.name)
        o.Label = i.name
        o.Shape = shapes[i.name]
        groups[i.kind].addObject(o)
        if App.GuiUp:
            o.ViewObject.ShapeColor = i.color
            if i.kind == "ref":
                o.ViewObject.Transparency = 80
        objs.append(o)
    doc.recompute()

    if os.environ.get("TVC_EXPORT", "1") != "0":
        import Import
        import MeshPart
        os.makedirs(os.path.join(out_dir, "stl"), exist_ok=True)
        App.ParamGet("User parameter:BaseApp/Preferences/Document").SetInt("CountBackupFiles", 0)
        doc.saveAs(os.path.join(out_dir, "tvc_compact.FCStd"))
        Import.export([o for o in objs if o.Name != "tube_ref"], os.path.join(out_dir, "tvc_compact_assembly.step"))
        neutral, _ = pose(items, 0, 0)
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
