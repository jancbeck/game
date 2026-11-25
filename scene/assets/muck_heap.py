"""Stable muck heap against a curtain wall, with the barrow that feeds it.

Footprint 2.1 m along the wall (X) by 1.4 m deep (Y), plus the barrow and the wet seep in front.
The wall is at local y = +0.75 and the open front faces -Y, so place the prop with its +Y side to
the wall face. Built at full size, so use scale 1.

The heap is about 0.75 m high: an old, dark, settled core of dung and rotted straw, with fresher
barrow loads tipped on its front and top, still yellow with straw. Two low plank kerbs between
driven stakes hold its ends; the front is open for the barrow. A plank runs from the ground up
onto the heap, a muck fork is stuck in the top, and dark liquor seeps out of the foot into a
flat wet stain. The barrow is a plank tray on two shafts with a solid wheel of three boards,
parked in front with its legs down and a last load of muck in it.
"""

import math

from . import _se_mesh as sm

HALF_X = 1.05
BACK_Y = 0.72


def _kerbs(kit, mats, rng, root):
    wd, wo = mats["wood_dark"], mats["wood_old"]
    for e in (-1, 1):
        x = e * HALF_X
        for k, y in enumerate((-0.6, 0.05, BACK_Y - 0.05)):
            kit.beam(f"stake_{e}_{k}", (x, y, -0.15), (x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.02, 0.02),
                                                       rng.uniform(0.52, 0.62)), (0.07, 0.07), wd, parent=root)
        for k in range(3):
            z = 0.1 + k * 0.17 + rng.uniform(-0.01, 0.01)
            if e < 0 and k == 2:
                # the top board split off at the front and was never replaced
                y0 = -0.05
            else:
                y0 = -0.66
            kit.beam(f"kerb_{e}_{k}", (x - e * 0.05, y0, z), (x - e * 0.05, BACK_Y, z + rng.uniform(-0.02, 0.02)),
                     (0.03, 0.165), wo if k else wd, bevel=0.004, parent=root)


def _heap(kit, mats, rng, root):
    old = sm.Mesh()
    old.dome((0.0, 0.18, -0.02), (1.0, 0.62, 0.72), rng, jitter=0.12)
    for _ in range(6):
        old.dome((rng.uniform(-0.75, 0.75), rng.uniform(-0.15, 0.5), rng.uniform(0.0, 0.25)),
                 (rng.uniform(0.3, 0.45), rng.uniform(0.25, 0.35), rng.uniform(0.25, 0.4)), rng, jitter=0.2)
    old.finish("muck_old", mats["mud"], root, smooth=True)
    # fresh loads: straw-bright lumps on the front slope and on top
    fresh = sm.Mesh()
    for (x, y, z, r) in ((-0.35, -0.32, 0.05, 0.36), (0.3, -0.38, 0.02, 0.3), (0.05, 0.05, 0.45, 0.32),
                         (0.6, -0.1, 0.25, 0.26)):
        fresh.dome((x + rng.uniform(-0.05, 0.05), y, z), (r, r * 0.8, r * 0.55), rng, jitter=0.25)
    fresh.finish("muck_fresh", mats["burlap"], root, smooth=True)
    stalks = sm.Mesh()
    for _ in range(220):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.random())
        x, y = 0.95 * r * math.cos(a), 0.18 + 0.6 * r * math.sin(a)
        z = 0.7 * math.sqrt(max(0.0, 1 - r * r)) + rng.uniform(-0.04, 0.02)
        stalks.box((0.011, 0.011, rng.uniform(0.12, 0.3)), (x, y, max(z, 0.02)),
                   (rng.uniform(-80, 80), rng.uniform(-80, 80), rng.uniform(0, 180)))
    stalks.finish("muck_straw", mats["straw"], root)
    dung = sm.Mesh()
    for _ in range(26):
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        r = rng.uniform(0.4, 0.95)
        x, y = 0.95 * r * math.cos(a), 0.18 + 0.62 * r * math.sin(a)
        z = 0.7 * math.sqrt(max(0.0, 1 - r * r)) * 0.9
        dung.dome((x, y, z), (0.05, 0.045, 0.04), rng, jitter=0.2)
    dung.finish("muck_dung", mats["bark"], root, smooth=True)
    # seep: a flat wet stain spreading from the foot
    seep = sm.Mesh()
    for _ in range(7):
        seep.dome((rng.uniform(-0.9, 0.9), rng.uniform(-0.95, -0.45), -0.012),
                  (rng.uniform(0.25, 0.45), rng.uniform(0.18, 0.3), 0.022), rng, jitter=0.3)
    seep.finish("muck_seep", mats["feather"], root, smooth=True)


def _plank_and_fork(kit, mats, rng, root):
    wo, iron = mats["wood_old"], mats["iron"]
    kit.beam("barrow_plank", (0.15, -1.05, 0.02), (0.08, 0.12, 0.62), (0.26, 0.035), wo, bevel=0.004, parent=root)
    # muck fork: four tines in the heap, the shaft leaning out toward the front
    base = (0.5, 0.25, 0.42)
    top = (0.78, -0.35, 1.68)
    kit.beam("fork_shaft", base, top, (0.034, 0.034), wo, bevel=0.004, parent=root)
    for k, dx in enumerate((-0.075, -0.025, 0.025, 0.075)):
        kit.beam(f"fork_tine_{k}", (base[0] + dx, base[1], base[2] + 0.02),
                 (base[0] + dx * 1.1 - 0.05, base[1] + 0.12, base[2] - 0.22), (0.012, 0.012), iron, parent=root)


def _barrow(kit, mats, rng, root):
    """Plank barrow parked in front of the heap, wheel toward the heap, handles toward the yard."""
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    g = kit.group("barrow", (-0.55, -1.35, 0.0), parent=root)
    g.rotation_euler = (0, 0, math.radians(rng.uniform(-28, -18)))
    r = 0.22
    # shafts: from the wheel axle at +Y back to the handles at -Y, rising toward the handles
    for sx in (-1, 1):
        kit.beam(f"shaft_{sx}", (sx * 0.2, 0.52, r), (sx * 0.27, -0.95, 0.5), (0.05, 0.06), wd, bevel=0.004,
                 parent=g)
        kit.beam(f"leg_{sx}", (sx * 0.24, -0.35, 0.42), (sx * 0.25, -0.38, 0.0), (0.05, 0.05), wd, parent=g)
    # tray: bottom and sides between the shafts
    tz = 0.36
    kit.box("tray_bottom", (0.5, 0.72, 0.025), (0, 0.02, tz), (-9, 0, 0), wo, parent=g)
    for sx in (-1, 1):
        kit.box(f"tray_side_{sx}", (0.025, 0.75, 0.24), (sx * 0.26, 0.02, tz + 0.12), (-9, 0, sx * 3), wo,
                bevel=0.003, parent=g)
    kit.box("tray_front", (0.55, 0.025, 0.3), (0, 0.42, tz + 0.16), (18, 0, 0), wo, bevel=0.003, parent=g)
    kit.box("tray_back", (0.5, 0.025, 0.22), (0, -0.36, tz + 0.06), mat=wo, bevel=0.003, parent=g)
    # solid wheel of three boards with an iron tyre, on an axle between the shaft ends
    for k, dz in enumerate((-0.14, 0.0, 0.14)):
        hw = math.sqrt(max(r * r - dz * dz, 0.0)) * 2
        kit.box(f"wheel_board_{k}", (0.045, hw, 0.14), (0, 0.55, r + dz), mat=wd, parent=g)
    kit.torus("wheel_tyre", r, 0.012, (0, 0.55, r), (0, 90, 0), iron, major_segments=20, minor_segments=4,
              parent=g)
    kit.cylinder("axle", 0.022, 0.46, (0, 0.55, r), (0, 90, 0), wo, segments=8, parent=g)
    load = sm.Mesh()
    load.dome((0, 0.05, tz + 0.12), (0.22, 0.32, 0.12), rng, jitter=0.25)
    load.finish("barrow_load", mats["mud"], g, smooth=True)
    st = sm.Mesh()
    for _ in range(40):
        st.box((0.01, 0.01, rng.uniform(0.1, 0.25)), (rng.uniform(-0.2, 0.2), rng.uniform(-0.25, 0.3),
                                                      tz + rng.uniform(0.1, 0.24)),
               (rng.uniform(-80, 80), rng.uniform(-80, 80), rng.uniform(0, 180)))
    st.finish("barrow_straw", mats["straw"], g)


def build(kit, mats, rng):
    root = kit.group("muck_heap")
    _kerbs(kit, mats, rng, root)
    _heap(kit, mats, rng, root)
    _plank_and_fork(kit, mats, rng, root)
    _barrow(kit, mats, rng, root)
    return root
