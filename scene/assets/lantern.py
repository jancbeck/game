"""Iron lantern with a lit tallow candle: about 0.42 m tall, hung from a wall bracket or standing.

The variant comes from the rng (50/50) unless `build` is called with `hanging`; the modules
lantern_hanging and lantern_standing do that, so a plan entry picks its variant by module name:

- hanging: origin is the mount point on the wall (XZ plane at y = 0). A back plate carries an
  arm that sticks out toward -Y with a brace under it. The lantern hangs below the arm tip on a
  short chain, so its flame is about 0.47 m under the mount point.
- standing: footprint centered on X/Y = 0, rests on Z = 0.

The cage is four posts, two frames, a pyramid cap with a vent and a ring handle. Four horn panes
glow with the `fire` material. The flame and the panes are the only emitters. LIGHTS is set by
build() to the chosen variant, and build_scene.py reads it after build().
"""

import math

from . import _fire

COLOR = (1.0, 0.50, 0.16)
WATTS_STANDING = 25.0      # a standing lantern lights the surface it sits on from 0.15 m: keep it low
WATTS_HANGING = 40.0       # a hanging one is 0.4 m from the wall and lights a wider patch
FLAME_Z = 0.155            # flame center above the lantern's base
ARM = 0.42                 # how far the arm reaches from the wall
HANG_Z0 = -0.625           # base of a hanging lantern relative to the mount point

LIGHTS_STANDING = [((0.0, 0.0, FLAME_Z), COLOR, WATTS_STANDING)]
LIGHTS_HANGING = [((0.0, -ARM, HANG_Z0 + FLAME_Z), COLOR, WATTS_HANGING)]
LIGHTS = LIGHTS_STANDING


def _lantern(kit, mats, rng, root, x, y, z0, sway):
    """Cage, candle and flame with the base at (x, y, z0)."""
    iron, wax, fire = mats["iron"], mats["cloth_emblem"], mats["fire"]
    grp = kit.group("lantern", (x, y, z0), parent=root)
    grp.rotation_euler = (math.radians(sway[0]), math.radians(sway[1]), math.radians(sway[2]))
    h = 0.07            # post offset from the center
    top = 0.285         # top frame height
    bar = 0.016

    # base pan with a lip, then three little feet
    kit.box("pan", (0.175, 0.175, 0.022), (0, 0, 0.011), mat=iron, bevel=0.004, parent=grp)
    kit.box("pan_lip", (0.19, 0.19, 0.012), (0, 0, 0.028), mat=iron, bevel=0.003, parent=grp)

    # four corner posts, a frame at the bottom and the top, a thinner mid band
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        kit.beam(f"post_{i}", (sx * h, sy * h, 0.034), (sx * h, sy * h, top), section=(bar, bar),
                 mat=iron, bevel=0.002, parent=grp)
    for name, z, t in (("frame_lo", 0.05, bar), ("frame_mid", 0.17, bar * 0.7),
                       ("frame_hi", top, bar * 1.2)):
        kit.box(f"{name}_x0", (2 * h + t, t, t), (0, -h, z), mat=iron, parent=grp)
        kit.box(f"{name}_x1", (2 * h + t, t, t), (0, h, z), mat=iron, parent=grp)
        kit.box(f"{name}_y0", (t, 2 * h + t, t), (-h, 0, z), mat=iron, parent=grp)
        kit.box(f"{name}_y1", (t, 2 * h + t, t), (h, 0, z), mat=iron, parent=grp)

    # horn panes: warm translucent glow between the posts (no shadow, so the flame's light escapes)
    zc, ph = (0.06 + top) / 2, top - 0.07
    for i, sy in enumerate((-1, 1)):
        kit.box(f"pane_y{i}", (2 * h - 0.012, 0.004, ph), (0, sy * (h - 0.004), zc), mat=fire,
                parent=grp)
        kit.box(f"pane_x{i}", (0.004, 2 * h - 0.012, ph), (sy * (h - 0.004), 0, zc), mat=fire,
                parent=grp)

    # hinged glass door on the front: a thin vertical bar and its latch
    kit.box("door_bar", (0.008, 0.008, top - 0.05), (0.0, -h - 0.004, 0.17), mat=iron, parent=grp)
    kit.box("latch", (0.03, 0.01, 0.014), (0.0, -h - 0.009, 0.17), mat=iron, parent=grp)

    # pyramid cap, vent chimney with a rain hat, and the ring handle
    kit.cylinder("cap", 0.125, 0.07, (0, 0, top + 0.035), rot_deg=(0, 0, 45), mat=iron, segments=4,
                 radius_top=0.032, bevel=0.003, parent=grp)
    kit.cylinder("chimney", 0.028, 0.04, (0, 0, top + 0.09), mat=iron, segments=8, parent=grp)
    kit.cylinder("hat", 0.056, 0.026, (0, 0, top + 0.122), mat=iron, segments=8, radius_top=0.012,
                 parent=grp)
    kit.torus("handle", 0.044, 0.0065, (0, 0, top + 0.17), rot_deg=(90, 0, 0), mat=iron,
              major_segments=16, minor_segments=5, parent=grp)

    # candle: iron cup, tallow stub, small flame
    kit.cylinder("cup", 0.034, 0.014, (0, 0, 0.045), mat=iron, segments=10, radius_top=0.026,
                 parent=grp)
    kit.cylinder("candle", 0.016, 0.072, (0, 0, 0.088), mat=wax, segments=8, parent=grp)
    _fire.flame(kit, fire, grp, "flame", (0, 0, 0.122), 0.11, 0.025, lean=(0.04, -0.03),
                twist=1.0, phase=kit.jitter(rng, 3.0), rings=10, sides=8)
    return grp


def _bracket(kit, mats, root):
    """Wall plate, arm with a brace, hook, ring and a short chain; returns the chain's bottom z."""
    iron = mats["iron"]
    kit.box("plate", (0.10, 0.03, 0.26), (0, -0.015, -0.03), mat=iron, bevel=0.006, parent=root)
    for i, (x, z) in enumerate(((-0.03, 0.06), (0.03, 0.06), (-0.03, -0.12), (0.03, -0.12))):
        kit.cylinder(f"rivet_{i}", 0.009, 0.012, (x, -0.034, z), rot_deg=(90, 0, 0), mat=iron,
                     segments=8, parent=root)
    kit.beam("arm", (0, -0.03, 0.0), (0, -ARM, 0.0), section=(0.024, 0.024), mat=iron,
             bevel=0.004, parent=root)
    kit.beam("brace", (0, -0.03, -0.17), (0, -ARM * 0.72, -0.012), section=(0.016, 0.016),
             mat=iron, bevel=0.003, parent=root)
    kit.torus("scroll", 0.045, 0.007, (0, -0.19, -0.075), rot_deg=(0, 90, 0), mat=iron,
              major_segments=16, minor_segments=5, parent=root)
    # hook at the tip, then ring and chain
    kit.beam("hook", (0, -ARM, 0.0), (0, -ARM, -0.05), section=(0.014, 0.014), mat=iron,
             parent=root)
    z = -0.075
    for i in range(5):
        rot = (90, 0, 0) if i % 2 == 0 else (0, 90, 0)
        kit.torus(f"link_{i}", 0.016, 0.0045, (0, -ARM, z), rot_deg=rot, mat=iron,
                  major_segments=10, minor_segments=4, parent=root)
        z -= 0.026
    return z


def build(kit, mats, rng, hanging=None):
    global LIGHTS
    if hanging is None:
        hanging = rng.random() < 0.5
    sway = (kit.jitter(rng, 1.5), kit.jitter(rng, 1.5), kit.jitter(rng, 30.0))
    if hanging:
        root = kit.group("lantern_hanging")
        _bracket(kit, mats, root)
        _lantern(kit, mats, rng, root, 0.0, -ARM, HANG_Z0, sway)
        LIGHTS = LIGHTS_HANGING
    else:
        root = kit.group("lantern_standing")
        _lantern(kit, mats, rng, root, 0.0, 0.0, 0.0, (0.0, 0.0, sway[2]))
        LIGHTS = LIGHTS_STANDING
    return root
