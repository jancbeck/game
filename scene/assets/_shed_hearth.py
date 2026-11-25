"""Fires of the cookhouse: open hearth under a masonry hood, stone chimney stack and bread oven.

Shed space: X east, Y toward the tower wall (+Y), Z up. The tower face is at y = 2.13; the NW
tower's corner is at x = 0.075, east of it the wall is the gatehouse.

- The hearth stands against the tower at x = HEARTH_X, under a tapering stone hood that leads into
  the stack. A cauldron hangs over the fire from the hood lintel. Tongs and poker lean on the
  right jamb, so the store door left of the hearth stays clear.
- The stack climbs the tower face between two rafters, through the roof, to STACK_TOP. All of it
  stands on the tower (west of x = -0.23), not on the gatehouse. Its crown is an open, sooty flue
  with a low front wall. From the courtyard camera it shows dark brick, a faint ember glow low on
  the back wall and the smoke plume above; there is no flame in it.
- The bread oven stands in the front bay, mouth to the south, where the main camera looks in.
"""

import bpy

from . import _fire
from . import _shed_geo as geo
from . import _shed_roof as roof

WALL_Y = 2.13
STACK_TOP = 7.25
STACK_CX = (roof.STACK_X[0] + roof.STACK_X[1]) / 2
STACK_CY = 1.66
CROWN_Z0 = 6.80                    # top of the upper corbel: the crown walls stand on it
FLUE_GLOW_Z = 6.82
HEARTH_X = -0.67                   # center line of hearth, hood and stack
HEARTH_K = 0.8                     # hearth width relative to a 1.7 m hob
HEARTH_FIRE = (HEARTH_X, 1.64, 0.3)  # coal bed center
OVEN = (0.62, -0.36)               # center of the oven platform
OVEN_FLOOR_Z = 0.80                # floor of the oven chamber


def _dressed(mat):
    """The wall material with `dressed` on: one chiseled stone per piece, paler than the rubble (as the gate's)."""
    copy = bpy.data.materials.get("stone_dressed")
    if copy is None:
        copy = mat.copy()
        copy.name = "stone_dressed"
        copy.node_tree.nodes["dressed"].outputs[0].default_value = 1.0
    return copy


def _faint_glow():
    """Dull red emission for the few live coals at the foot of the flue: bright enough to see, too dim to bloom."""
    mat = bpy.data.materials.get("flue_ember")
    if mat is None:
        mat = bpy.data.materials.new("flue_ember")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 14.0
        noise.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.30, 0.03, 0.005, 1.0)
        ramp.color_ramp.elements[1].color = (0.85, 0.16, 0.03, 1.0)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.inputs["Strength"].default_value = 0.45
        nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _hx(x):
    """X of a hearth part laid out for a 1.7 m hob centered on x = 0.5, moved and narrowed to HEARTH_X."""
    return HEARTH_X + (x - 0.5) * HEARTH_K


def hearth(kit, mats, rng, root):
    st, wd, iron = mats["stone_wall"], mats["wood_dark"], mats["iron"]
    K, X = HEARTH_K, _hx
    embers, fire = mats["embers"], mats["fire"]
    fx, fy, fz = HEARTH_FIRE

    kit.box("hearth_base", (1.7 * K, 1.1, 0.26), (X(0.5), 1.55, 0.13), mat=st, bevel=0.02, parent=root)
    for n, x in enumerate((X(-0.19), X(1.19))):
        kit.box(f"hood_jamb_{n}", (0.24 * K, 0.26, 1.29), (x, 1.17, 0.26 + 0.645), mat=st, bevel=0.015, parent=root)
    kit.box("hood_lintel", (1.78 * K, 0.22, 0.18), (X(0.5), 1.15, 1.64), mat=wd, bevel=0.012, parent=root)
    hood = geo.Mesh()
    hood.prism(geo.rect(X(-0.32), X(1.32), 1.04, 2.13, 1.73), geo.rect(roof.STACK_X[0], roof.STACK_X[1], 1.30, 2.13, 2.75))
    hood.finish("hood", st, root, bevel=0.012)
    kit.box("hood_throat", (roof.STACK_X[1] - roof.STACK_X[0], 0.86, 0.2), (STACK_CX, 1.73, 2.7), mat=st, parent=root)
    # iron plate behind the fire reflects it and keeps the tower wall from cracking
    kit.box("fireback", (0.95 * K, 0.04, 0.8), (X(0.5), WALL_Y - 0.03, 0.66), mat=iron, bevel=0.006, parent=root)

    # fire: crossed logs, a bed of coals, tongues of flame
    logs = geo.Mesh()
    for p0, p1 in (((0.12, 1.52, 0.32), (0.86, 1.76, 0.35)), ((0.2, 1.82, 0.32), (0.82, 1.48, 0.34)),
                   ((0.44, 1.46, 0.40), (0.56, 1.86, 0.44))):
        logs.cyl((X(p0[0]),) + p0[1:], (X(p1[0]),) + p1[1:], 0.055, 0.05, sides=7)
    logs.finish("hearth_logs", wd, root)
    kit.sphere("hearth_coals", 0.3 * K, (fx, fy, fz - 0.02), scale=(1.0, 0.78, 0.3), mat=embers, segments=14,
               parent=root)
    for n, (dx, dy, h, r, lean) in enumerate(((-0.08, -0.02, 0.62, 0.12, (0.0, 0.14)), (0.14, 0.05, 0.5, 0.11, (0.04, 0.12)),
                                              (0.0, -0.1, 0.38, 0.09, (-0.02, 0.08)), (-0.2, 0.06, 0.3, 0.08, (-0.06, 0.1)))):
        _fire.flame(kit, fire, root, f"hearth_flame_{n}", (fx + dx * K, fy + dy, fz + 0.05), h, r, lean=lean,
                    twist=1.2 + n * 0.4, phase=n * 2.1)

    # cauldron on a chain from the lintel, flames licking its belly
    cx, cy = HEARTH_X, 1.5
    kit.cylinder("chain_rod", 0.01, 0.34, (cx, cy, 1.38), mat=iron, segments=6, parent=root)
    for n in range(5):
        kit.torus(f"chain_link_{n}", 0.022, 0.006, (cx, cy, 1.24 - 0.065 * n), (90 * (n % 2), 90 * ((n + 1) % 2), 0),
                  iron, major_segments=10, minor_segments=4, parent=root)
    kit.cylinder("cauldron", 0.19, 0.34, (cx, cy, 0.76), mat=iron, radius_top=0.28, segments=18, bevel=0.006,
                 parent=root)
    kit.cylinder("cauldron_broth", 0.255, 0.02, (cx, cy, 0.905), mat=wd, segments=18, parent=root)
    kit.torus("cauldron_rim", 0.28, 0.016, (cx, cy, 0.93), mat=iron, major_segments=18, minor_segments=5, parent=root)
    kit.torus("cauldron_bail", 0.28, 0.008, (cx, cy, 0.93), (90, 0, 0), iron, major_segments=18, minor_segments=4,
              parent=root)

    # tongs, poker and a bellows leaned against the left jamb; ash and charcoal on the apron
    kit.beam("poker", (X(1.04), 1.02, 0.28), (X(1.02), 1.2, 1.05), (0.016, 0.016), iron, parent=root)
    kit.beam("fire_tongs", (X(1.1), 1.0, 0.28), (X(1.12), 1.18, 1.0), (0.02, 0.012), iron, parent=root)
    ash = geo.Mesh()
    for _ in range(24):
        px, py = rng.gauss(HEARTH_X, 0.3), rng.uniform(1.04, 1.3)
        s = rng.uniform(0.015, 0.04)
        ash.box((s, s * rng.uniform(0.6, 1.3), s * 0.6), (px, py, 0.26 + s * 0.25),
                (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(0, 180)))
    ash.finish("hearth_ash", iron, root)


def stack(kit, mats, rng, root):
    """Rubble stack from the hood to STACK_TOP, with pale dressed-stone bands, corbels, a sooty crown and soot streaks."""
    st = mats["stone_wall"]
    cut = _dressed(st)
    x0, x1 = roof.STACK_X
    y0, y1 = roof.STACK_Y
    cx = STACK_CX
    z0, z1 = 2.7, 6.5
    kit.box("stack_shaft", (x1 - x0, y1 - y0, z1 - z0), (cx, (y0 + y1) / 2, (z0 + z1) / 2), mat=st, bevel=0.012,
            parent=root)
    for n, z in enumerate((4.9, 5.7)):
        kit.box(f"stack_band_{n}", (x1 - x0 + 0.1, y1 - y0 + 0.05, 0.1), (cx, (y0 - 0.05 + y1) / 2, z), mat=cut,
                bevel=0.012, parent=root)
    for n, (grow, z) in enumerate(((0.05, 6.575), (0.1, 6.725))):
        ya = y0 - grow
        kit.box(f"stack_corbel_{n}", (x1 - x0 + 2 * grow, y1 - ya, 0.15), (cx, (ya + y1) / 2, z), mat=cut,
                bevel=0.008, parent=root)
    # crown: four walls round the flue, the south one lower; the flue floor is soot
    ya = y0 - 0.12
    xl, xr = cx - 0.43, cx + 0.43
    fw, fd = 0.2, 0.25                       # flue half width and half depth
    h_front, h_back = 0.32, STACK_TOP - CROWN_Z0
    kit.box("crown_south", (xr - xl, 0.25, h_front), (cx, ya + 0.125, CROWN_Z0 + h_front / 2), mat=cut, bevel=0.008,
            parent=root)
    kit.box("crown_north", (xr - xl, y1 - (STACK_CY + fd), h_back), (cx, (y1 + STACK_CY + fd) / 2,
                                                                    CROWN_Z0 + h_back / 2),
            mat=cut, bevel=0.008, parent=root)
    for n, s in enumerate((-1, 1)):
        xa, xb = (xl, cx - fw) if s < 0 else (cx + fw, xr)
        kit.box(f"crown_side_{n}", (xb - xa, 2 * fd, h_back), ((xa + xb) / 2, STACK_CY, CROWN_Z0 + h_back / 2),
                mat=cut, bevel=0.008, parent=root)
    soot = mats["wood_dark"]
    kit.box("flue_floor", (2 * fw, 2 * fd, 0.02), (cx, STACK_CY, CROWN_Z0 + 0.01), mat=soot, parent=root)
    # a low, faint ember glow where the draught still keeps a few coals alive in the throat
    kit.box("flue_glow_wall", (0.26, 0.02, 0.09), (cx + 0.04, STACK_CY + fd - 0.012, FLUE_GLOW_Z + 0.05),
            mat=_faint_glow(), parent=root)
    kit.box("flue_glow", (0.18, 0.12, 0.012), (cx + 0.04, STACK_CY + fd - 0.08, FLUE_GLOW_Z), mat=_faint_glow(),
            parent=root)
    # soot running down the shaft from under the corbels, and over the crown's front face
    for n, (dx, w, drop) in enumerate(((-0.24, 0.07, 0.62), (-0.09, 0.1, 0.28), (0.05, 0.06, 0.8),
                                       (0.16, 0.09, 0.42), (0.26, 0.05, 0.55))):
        kit.box(f"soot_{n}", (w, 0.012, drop), (cx + dx, y0 - 0.006, z1 - drop / 2 - 0.02), mat=soot, parent=root)
    for n, (dx, w, drop) in enumerate(((-0.28, 0.09, 0.20), (0.0, 0.12, 0.12), (0.24, 0.08, 0.24))):
        kit.box(f"crown_soot_{n}", (w, 0.012, drop), (cx + dx, ya - 0.006, CROWN_Z0 + h_front - drop / 2), mat=soot,
                parent=root)


def smoke_and_sparks(kit, mats, rng, root):
    """Smoke plume over the crown, blown east like the other fires, and three sparks that rise with it."""
    top = (STACK_CX, STACK_CY, STACK_TOP)
    _fire.smoke(kit, mats["smoke"], root, "chimney_smoke", base=top, rise=1.8, drift=2.2, r0=0.32, r1=1.5,
                density=1.5, seed=rng.uniform(0, 50))
    _fire.sparks(kit, mats["embers"], root, "chimney_sparks", rng, 3, (STACK_CX, STACK_CY, STACK_TOP - 0.1), 1.6,
                 0.08, (0.9, 0.2), 0.035)


def oven(kit, mats, rng, root):
    """Beehive bread oven on a stone platform. The mouth faces -Y and is cut through the facade and dome."""
    st, iron, wo = mats["stone_wall"], mats["iron"], mats["wood_old"]
    embers, fire = mats["embers"], mats["fire"]
    ox, oy = OVEN
    top = 0.78
    kit.box("oven_base", (0.86, 0.84, top), (ox, oy, top / 2), mat=st, bevel=0.02, parent=root)
    dome = kit.sphere("oven_dome", 1.0, (ox, oy + 0.04, top), scale=(0.4, 0.36, 0.42), mat=st, segments=20,
                      parent=root)
    facade = kit.box("oven_facade", (0.72, 0.26, 0.5), (ox, oy - 0.26, top + 0.25), mat=st, bevel=0.012,
                     parent=root)
    mw, mh, md = 0.42, 0.34, 0.46           # mouth width, height and depth into the dome
    y_front = oy - 0.39
    cutter = kit.box("oven_mouth_cut", (mw, md + 0.05, mh), (ox, y_front + md / 2 - 0.025, OVEN_FLOOR_Z + mh / 2),
                     parent=root)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    for ob in (dome, facade):
        mod = ob.modifiers.new("mouth", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
    # coal bed on the floor of the chamber, low flames above it, soot-black arch stone
    kit.box("oven_coals", (mw - 0.04, md - 0.1, 0.07), (ox, y_front + md / 2 + 0.05, OVEN_FLOOR_Z + 0.025),
            mat=embers, parent=root)
    for n, (dx, dy, h, r) in enumerate(((-0.12, 0.2, 0.27, 0.06), (0.0, 0.3, 0.3, 0.07), (0.12, 0.22, 0.22, 0.055))):
        _fire.flame(kit, fire, root, f"oven_flame_{n}", (ox + dx, y_front + dy, OVEN_FLOOR_Z + 0.05), h, r,
                    lean=(0.0, -0.1), twist=1.0 + n, phase=1.3 + n * 2.0)
    kit.box("oven_sill", (0.56, 0.12, 0.05), (ox, y_front - 0.04, OVEN_FLOOR_Z - 0.025), mat=st, bevel=0.01,
            parent=root)
    # iron door leaned against the platform, a baker's peel against the facade
    kit.box("oven_door", (0.4, 0.035, 0.36), (ox + 0.5, oy - 0.5, 0.2), (-8, 0, 12), iron, bevel=0.008, parent=root)
    kit.beam("oven_peel", (ox - 0.52, oy - 0.55, 0.03), (ox - 0.42, oy - 0.33, 1.55), (0.035, 0.026), wo, bevel=0.004,
             parent=root)
    kit.box("oven_peel_blade", (0.3, 0.012, 0.26), (ox - 0.53, oy - 0.56, 0.15), (-3, 0, 4), wo, bevel=0.003,
            parent=root)
