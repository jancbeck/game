"""Ground mist: a thin, patchy layer of rain mist lying on the courtyard floor.

Place it once, at the origin, unrotated and at scale 1: `"ground_mist": {"pos": [0, 0], "rot_z": 0}`.
It reads the floor polygon (`platform.polygon`) from the location's plan.json itself.

The layer is a volume (Principled Volume) in a box over the floor's bounding box, from just under
the floor up to 0.55 m. EEVEE evaluates a volume object over its whole bounding box, so the shape
of the floor is cut out by a mask image made here from the polygon, with soft edges: no mist
drifts out over the lower ward beyond the parapet or into the wall feet.

Density, per meter, at the floor:

- falls off exponentially with height (a scale height of 0.17 m) and is gone at the top of the box;
- is broken into patches by large noise and into wisps by finer noise, so some of the floor is
  clear and some is deep in it;
- is zero outside the mask.

The noise drifts slowly with the scene time, so the mist moves when frames advance. The mist is
bluish grey and scatters the light of the fires, so it glows warm near them. It casts no shadow.
Its density is small enough that the floor, the props and the walls read through it.

A thin layer needs fine depth slices, so a render_pre handler fits EEVEE's volume range to the camera
before every frame (see `_fit_volume_range`), and the same handler scales the density by ORTHO_GAIN for an
orthographic camera, because a steep view crosses far less of a thin layer than a standing person's.
"""

import math

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

import location
from planlib import inside_polygon as _inside


TOP = 0.55                    # layer height above the floor, meters
BELOW = 0.05                  # box starts this far below the floor, so the floor is inside it
DENSITY = 0.6                # density per meter at the floor in the thickest patch
SCALE_HEIGHT = 0.17           # meters over which the density falls to 1/e
COLOR = (0.50, 0.56, 0.66)
ANISOTROPY = 0.35
ORTHO_GAIN = 4.0              # an orthographic camera looks down steeply, through a third of the mist a person sees
MASK_RES = 0.12               # meters per mask pixel
MASK_SOFT = 0.9               # meters over which the mask fades in from the floor's edge
DRIFT = 0.04                  # noise units per second
FPS = 24.0


@persistent
def _fit_volume_range(scene, *_):
    """Spread EEVEE's volume slices over the depth the scene occupies.

    With the default range (0.1 to 100 m, most slices near the camera) a layer half a meter thick
    that is 45 m away from the orthographic camera falls between two slices and almost vanishes.
    The range is fitted to the camera before every frame: for an orthographic camera, 32 m either side
    of the castle's center, evenly spread; for a perspective camera, from the lens to 60 m.
    A camera that moves between the two (scene/descent.py) sets its own values as custom
    properties: `mist_gain`, and `volume_range` (start, end in m).
    """
    cam = scene.camera
    if cam is None or "ground_mist" not in bpy.data.materials:
        return
    ev = scene.eevee
    ev.use_volume_custom_range = True
    gain = bpy.data.materials["ground_mist"].node_tree.nodes.get("view_gain")
    if gain is not None:
        gain.outputs[0].default_value = cam.get("mist_gain", ORTHO_GAIN if cam.data.type == "ORTHO" else 1.0)
    if "volume_range" in cam:
        ev.volumetric_start, ev.volumetric_end = cam["volume_range"]
        ev.volumetric_sample_distribution = 0.3
    elif cam.data.type == "ORTHO":
        fwd = cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
        d = (Vector((0.0, -2.0, 0.0)) - cam.matrix_world.translation).dot(fwd)
        ev.volumetric_start, ev.volumetric_end = max(0.1, d - 32.0), d + 32.0
        ev.volumetric_sample_distribution = 0.0
    else:
        ev.volumetric_start, ev.volumetric_end = 0.1, 60.0
        ev.volumetric_sample_distribution = 0.6


def _dist_to_edge(px, py, poly):
    best = 1e9
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best


def _mask_image(poly, x0, y0, w, h):
    """Image of the floor: 1 inside, fading to 0 at the polygon's edge. One pixel is MASK_RES meters."""
    nx, ny = int(w / MASK_RES) + 1, int(h / MASK_RES) + 1
    img = bpy.data.images.new("ground_mist_mask", nx, ny, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    px = []
    for j in range(ny):
        y = y0 + j * MASK_RES
        for i in range(nx):
            x = x0 + i * MASK_RES
            v = 0.0
            if _inside(x, y, poly):
                t = min(1.0, _dist_to_edge(x, y, poly) / MASK_SOFT)
                v = t * t * (3 - 2 * t)
            px += [v, v, v, 1.0]
    img.pixels.foreach_set(px)
    img.pack()
    return img


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def _map(nt, value, lo, hi, to_lo=0.0, to_hi=1.0, smooth=True):
    m = nt.nodes.new("ShaderNodeMapRange")
    if smooth:
        m.interpolation_type = "SMOOTHSTEP"
    m.inputs["From Min"].default_value = lo
    m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = to_lo
    m.inputs["To Max"].default_value = to_hi
    nt.links.new(value, m.inputs["Value"])
    return m.outputs["Result"]


def _material(img, x0, y0, w, h):
    mat = bpy.data.materials.new("ground_mist")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])      # volume only: the box itself stays invisible
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    px, py, pz = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]

    # the floor's outline, from the mask image
    uv = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(_math(nt, "DIVIDE", _math(nt, "SUBTRACT", px, x0), w), uv.inputs["X"])
    nt.links.new(_math(nt, "DIVIDE", _math(nt, "SUBTRACT", py, y0), h), uv.inputs["Y"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    nt.links.new(uv.outputs[0], tex.inputs["Vector"])
    sepc = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex.outputs["Color"], sepc.inputs[0])
    mask = sepc.outputs["Red"]

    # height: exponential fall-off, closed off smoothly at the top of the box
    z = _math(nt, "MAXIMUM", pz, 0.0)
    fall = _math(nt, "POWER", 2.718281828, _math(nt, "MULTIPLY", z, -1.0 / SCALE_HEIGHT))
    top = _map(nt, pz, TOP, TOP * 0.55, 0.0, 1.0)
    vertical = _math(nt, "MULTIPLY", fall, top)

    # patches (large, slow) and wisps (finer, drifting with time)
    clock = nt.nodes.new("ShaderNodeValue")
    drv = clock.outputs[0].driver_add("default_value")
    drv.driver.type = "SCRIPTED"
    drv.driver.expression = f"frame / {FPS} * {DRIFT}"
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.noise_dimensions = "4D"
    big.inputs["Scale"].default_value = 0.30
    big.inputs["Detail"].default_value = 4.0
    nt.links.new(geo.outputs["Position"], big.inputs["Vector"])
    nt.links.new(clock.outputs[0], big.inputs["W"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.noise_dimensions = "4D"
    fine.inputs["Scale"].default_value = 1.4
    fine.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], fine.inputs["Vector"])
    nt.links.new(_math(nt, "MULTIPLY", clock.outputs[0], 3.0), fine.inputs["W"])
    patches = _map(nt, big.outputs["Fac"], 0.40, 0.68, 0.0, 1.0)
    wisps = _map(nt, fine.outputs["Fac"], 0.30, 0.70, 0.45, 1.25)

    density = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", vertical, mask),
                    _math(nt, "MULTIPLY", patches, wisps))
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "view_gain"
    gain.outputs[0].default_value = 1.0
    density = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", density, DENSITY), gain.outputs[0])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*COLOR, 1.0)
    vol.inputs["Anisotropy"].default_value = ANISOTROPY
    nt.links.new(density, vol.inputs["Density"])
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return mat


def build(kit, mats, rng):
    root = kit.group("ground_mist")
    poly = [tuple(p) for p in location.plan()["platform"]["polygon"]]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs) - 0.5, max(xs) + 0.5, min(ys) - 0.5, max(ys) + 0.5
    w, h = x1 - x0, y1 - y0
    img = _mask_image(poly, x0, y0, w, h)
    box = kit.box("mist", (w, h, TOP + BELOW), ((x0 + x1) / 2, (y0 + y1) / 2, (TOP - BELOW) / 2), parent=root)
    box.data.materials.append(_material(img, x0, y0, w, h))
    box.visible_shadow = False
    handlers = bpy.app.handlers.render_pre
    for fn in [f for f in handlers if f.__name__ == _fit_volume_range.__name__]:
        handlers.remove(fn)
    handlers.append(_fit_volume_range)
    return root
