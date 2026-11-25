"""Bucket or tub catching roof drips: rainwater inside, splash rings, a thread of drops above.

A wooden bucket (0.34 m rim, 0.35 m tall) or a larger tub-sized one (up to 0.54 m rim) stands on
Z = 0 with its bail folded over the rim, two thirds full of still rainwater. Concentric ripple
rings and a few crown droplets mark where the drip lands, a little off the center. A broken
thread of faint drops falls from `drip_height` (default 2.8 m, the shed's front eave) to the
water. The water and the ripples use private materials (`rainwater`, `ripple`), because the shared
library has no still-water material.
"""

import math

import bpy

from . import bucket as bucket_mod

EAVE_HEIGHT = 2.8


def _glossy(name, base, rough=0.02):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = base
        b.inputs["Roughness"].default_value = rough
        b.inputs["Specular IOR Level"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
    return mat


def _ripple_material():
    mat = bpy.data.materials.get("ripple")
    if mat is None:
        mat = _glossy("ripple", (0.06, 0.08, 0.1, 1.0), 0.1)
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (0.55, 0.65, 0.8, 1.0)
        b.inputs["Emission Strength"].default_value = 0.12
    return mat


def build(kit, mats, rng, drip_height=EAVE_HEIGHT, big=None):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("drip_bucket")
    big = rng.random() < 0.45 if big is None else big
    s = rng.uniform(1.35, 1.55) if big else rng.uniform(0.95, 1.1)
    b = bucket_mod.build(kit, mats, rng, bail_deg=rng.uniform(78, 102))
    b.parent = root
    b.scale = (s, s, s)
    b.rotation_euler = (0, 0, math.radians(rng.uniform(0, 360)))

    # still water two thirds up, with a faint rim of meniscus
    z_w = rng.uniform(0.2, 0.27)
    r_w = bucket_mod._r(z_w) - bucket_mod.WALL - 0.002
    n = 36
    verts = [(0, 0, z_w)] + [(r_w * math.cos(2 * math.pi * i / n), r_w * math.sin(2 * math.pi * i / n), z_w)
                             for i in range(n)]
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    kit.mesh("rainwater", verts, faces, mat=_glossy("rainwater", (0.03, 0.04, 0.05, 1.0)), parent=b)

    # ripple rings around the drip point
    ripple = _ripple_material()
    dx, dy = j(0.03), j(0.03)
    for k, r in enumerate((0.022, 0.05, 0.085)):
        if math.hypot(dx, dy) + r < r_w - 0.01:
            kit.torus(f"ripple_{k}", r, 0.0025 - 0.0004 * k, (dx, dy, z_w + 0.002), mat=ripple,
                      major_segments=28, minor_segments=4, parent=b)
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.01, 0.03)
        kit.sphere(f"crown_{k}", 0.004, (dx + d * math.cos(a), dy + d * math.sin(a), z_w + rng.uniform(0.01, 0.035)),
                   mat=mats["rain"], segments=5, parent=b)

    # thread of drops: dashes that spread out toward the eave
    z = z_w * s + 0.03
    tx, ty = dx * s, dy * s
    gap = 0.05
    while z < drip_height:
        length = rng.uniform(0.04, 0.09)
        kit.cylinder(f"drop_{int(z * 100)}", 0.0016, length, (tx + j(0.004), ty + j(0.004), z + length / 2),
                     mat=mats["rain"], segments=4, parent=root)
        z += length + gap
        gap *= 1.12
    return root
