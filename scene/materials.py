"""Shared material library: the whole scene uses the materials of SPECS.

Props ask for a material by key (`mats["wood_old"]`) and never create their
own. Textures are procedural and use object coordinates, which are meters
because kit.py keeps object scale at 1.
"""

import importlib.util
from pathlib import Path

import bpy

_OVERRIDES = Path(__file__).resolve().parent / "mats"

SPECS = {
    # masonry: block pattern on walls, towers, stairs, gate arch
    "stone_wall": {"kind": "brick", "a": (0.050, 0.056, 0.066), "b": (0.135, 0.140, 0.150),
                   "mortar": (0.018, 0.018, 0.020), "brick": (0.40, 0.21), "rough": (0.6, 0.95)},
    # courtyard floor: cobbles with wet, reflective patches
    "cobble_wet": {"kind": "cobble", "a": (0.040, 0.034, 0.026), "b": (0.120, 0.098, 0.066),
                   "grout": (0.012, 0.010, 0.008), "cell": 3.2, "rough": (0.08, 0.75)},
    # dry flagstones of a floor under a roof: larger stones than the courtyard's setts, no puddles
    "flagstone": {"kind": "cobble", "a": (0.050, 0.047, 0.042), "b": (0.135, 0.125, 0.108),
                  "grout": (0.020, 0.018, 0.014), "cell": 2.6, "rough": (0.42, 0.85)},
    # weathered planks: platforms, crates, cart, shed
    "wood_old": {"kind": "noise", "a": (0.040, 0.030, 0.020), "b": (0.125, 0.098, 0.068),
                 "scale": 14.0, "rough": (0.6, 0.95), "bump": 0.4},
    # heavy dark timber: posts, beams, gallows frame
    "wood_dark": {"kind": "noise", "a": (0.022, 0.016, 0.011), "b": (0.075, 0.055, 0.038),
                  "scale": 10.0, "rough": (0.55, 0.9), "bump": 0.4},
    # gate leaves: richer brown than the props
    "door_wood": {"kind": "noise", "a": (0.050, 0.028, 0.014), "b": (0.150, 0.088, 0.045),
                  "scale": 12.0, "rough": (0.5, 0.85), "bump": 0.35},
    # iron: bands, hoops, brackets, grate, brazier
    "iron": {"kind": "noise", "a": (0.020, 0.020, 0.022), "b": (0.090, 0.070, 0.055),
             "scale": 18.0, "rough": (0.35, 0.8), "bump": 0.2, "metallic": 0.85},
    "rope": {"kind": "noise", "a": (0.160, 0.120, 0.075), "b": (0.300, 0.235, 0.150),
             "scale": 30.0, "rough": (0.8, 1.0), "bump": 0.3},
    "cloth_red": {"kind": "noise", "a": (0.110, 0.012, 0.010), "b": (0.260, 0.035, 0.028),
                  "scale": 6.0, "rough": (0.75, 0.95), "bump": 0.15},
    # faded painted emblem on banners
    "cloth_emblem": {"kind": "noise", "a": (0.300, 0.270, 0.220), "b": (0.520, 0.470, 0.400),
                     "scale": 8.0, "rough": (0.8, 0.95), "bump": 0.1},
    "fire": {"kind": "emission", "color": (1.0, 0.30, 0.03), "strength": 2.5},
    "embers": {"kind": "emission", "color": (1.0, 0.16, 0.02), "strength": 1.2, "noise": True},
    "feather": {"kind": "noise", "a": (0.008, 0.008, 0.010), "b": (0.030, 0.030, 0.038),
                "scale": 20.0, "rough": (0.35, 0.6), "bump": 0.1},
    # ground outside the walls: trodden mud, standing water, dead grass
    "mud": {"kind": "noise", "a": (0.025, 0.022, 0.015), "b": (0.075, 0.066, 0.045),
            "scale": 2.0, "rough": (0.2, 0.9), "bump": 0.3},
    # bare rock of the castle spur: the cliff face, the scree and the rock strip at the south wall feet
    "rock": {"kind": "noise", "a": (0.030, 0.031, 0.032), "b": (0.150, 0.142, 0.128),
             "scale": 0.9, "rough": (0.25, 0.85), "bump": 1.0},
    # tree bark: trunks, branches, roots
    "bark": {"kind": "noise", "a": (0.020, 0.018, 0.015), "b": (0.070, 0.062, 0.052),
             "scale": 25.0, "rough": (0.7, 0.95), "bump": 0.6},
    # loose straw and hay, wet and grey with age
    "straw": {"kind": "noise", "a": (0.110, 0.090, 0.050), "b": (0.260, 0.210, 0.120),
              "scale": 40.0, "rough": (0.6, 0.9), "bump": 0.2},
    # sacks, tarps, rags
    "burlap": {"kind": "noise", "a": (0.080, 0.065, 0.045), "b": (0.170, 0.140, 0.100),
               "scale": 60.0, "rough": (0.8, 1.0), "bump": 0.25},
    # moss, weeds and grass tufts
    "moss": {"kind": "noise", "a": (0.020, 0.030, 0.012), "b": (0.060, 0.080, 0.030),
             "scale": 30.0, "rough": (0.6, 0.9), "bump": 0.3},
    # falling rain streaks and splash droplets: faint, cool, see-through
    "rain": {"kind": "emission", "color": (0.55, 0.62, 0.75), "strength": 0.12},
    # smoke above fires; scene/mats/smoke.py turns it into a volume
    "smoke": {"kind": "noise", "a": (0.05, 0.05, 0.05), "b": (0.12, 0.12, 0.12),
              "scale": 3.0, "rough": (1.0, 1.0), "bump": 0.0},
    # the kitchen: coals that glow in spots, cast iron, soup, milk, flour, ash, crusty bread
    "coals": {"kind": "noise", "a": (0.01, 0.01, 0.01), "b": (0.05, 0.04, 0.04),
              "scale": 20.0, "rough": (0.9, 1.0), "bump": 0.3},
    "cast_iron": {"kind": "noise", "a": (0.010, 0.010, 0.012), "b": (0.040, 0.038, 0.038),
                  "scale": 22.0, "rough": (0.45, 0.7), "bump": 0.1, "metallic": 0.6},
    "broth": {"kind": "noise", "a": (0.030, 0.021, 0.010), "b": (0.075, 0.052, 0.022),
              "scale": 14.0, "rough": (0.10, 0.35), "bump": 0.05},
    "milk": {"kind": "noise", "a": (0.30, 0.29, 0.26), "b": (0.42, 0.41, 0.37),
             "scale": 6.0, "rough": (0.08, 0.2), "bump": 0.02},
    "flour": {"kind": "noise", "a": (0.20, 0.19, 0.17), "b": (0.34, 0.32, 0.28),
              "scale": 25.0, "rough": (0.9, 1.0), "bump": 0.3},
    "ash": {"kind": "noise", "a": (0.015, 0.015, 0.016), "b": (0.07, 0.068, 0.065),
            "scale": 30.0, "rough": (0.9, 1.0), "bump": 0.3},
    "crust": {"kind": "noise", "a": (0.12, 0.065, 0.025), "b": (0.30, 0.17, 0.07),
              "scale": 14.0, "rough": (0.8, 0.95), "bump": 0.25},
    "crumb": {"kind": "noise", "a": (0.42, 0.34, 0.22), "b": (0.58, 0.48, 0.32),
              "scale": 40.0, "rough": (0.9, 1.0), "bump": 0.2},
    "clay": {"kind": "noise", "a": (0.10, 0.045, 0.022), "b": (0.22, 0.11, 0.055),
             "scale": 16.0, "rough": (0.55, 0.85), "bump": 0.1},
    # the yard around the cookhouse: wet flagstones (scene/mats/yard_paving.py builds them)
    "yard_paving": {"kind": "noise", "a": (0.05, 0.05, 0.05), "b": (0.1, 0.1, 0.1), "scale": 4.0, "rough": (0.3, 0.8), "bump": 0.2},
    # a table top scrubbed pale with sand and lye
    "scrubbed": {"kind": "noise", "a": (0.11, 0.085, 0.055), "b": (0.26, 0.20, 0.135),
                 "scale": 12.0, "rough": (0.7, 0.9), "bump": 0.35},
    # sacks in a store: dull dark brown burlap
    "sacking": {"kind": "noise", "a": (0.045, 0.034, 0.020), "b": (0.095, 0.072, 0.042),
                "scale": 60.0, "rough": (0.85, 1.0), "bump": 0.3},
    "cheese": {"kind": "noise", "a": (0.20, 0.12, 0.04), "b": (0.34, 0.22, 0.08),
               "scale": 10.0, "rough": (0.55, 0.8), "bump": 0.1},
    # the commander's chamber: wool, parchment, candle wax, pewter, a mail shirt, the painted map, the misty valley below the window
    "wool": {"kind": "noise", "a": (0.050, 0.046, 0.040), "b": (0.115, 0.105, 0.088),
             "scale": 70.0, "rough": (0.9, 1.0), "bump": 0.3},
    "wool_red": {"kind": "noise", "a": (0.045, 0.012, 0.010), "b": (0.115, 0.030, 0.024),
                 "scale": 60.0, "rough": (0.9, 1.0), "bump": 0.3},
    "parchment": {"kind": "noise", "a": (0.20, 0.17, 0.115), "b": (0.34, 0.29, 0.20),
                  "scale": 16.0, "rough": (0.7, 0.9), "bump": 0.1},
    "candle": {"kind": "noise", "a": (0.34, 0.30, 0.20), "b": (0.50, 0.45, 0.32),
               "scale": 20.0, "rough": (0.45, 0.65), "bump": 0.05},
    "pewter": {"kind": "noise", "a": (0.07, 0.07, 0.075), "b": (0.20, 0.20, 0.21),
               "scale": 24.0, "rough": (0.35, 0.6), "bump": 0.1, "metallic": 0.8},
    "mail": {"kind": "noise", "a": (0.03, 0.03, 0.034), "b": (0.12, 0.115, 0.115),
             "scale": 60.0, "rough": (0.4, 0.7), "bump": 0.3, "metallic": 0.85},
    "map_board": {"kind": "noise", "a": (0.2, 0.17, 0.115), "b": (0.34, 0.29, 0.2),
                  "scale": 16.0, "rough": (0.7, 0.9), "bump": 0.1},
    "water": {"kind": "noise", "a": (0.012, 0.018, 0.024), "b": (0.030, 0.040, 0.050),
              "scale": 5.0, "rough": (0.03, 0.10), "bump": 0.03},
    # the cliff rock around the commander's chamber: dull, dark, wet, with no sheen
    "cliff_rock": {"kind": "noise", "a": (0.016, 0.018, 0.020), "b": (0.085, 0.082, 0.078),
                   "scale": 1.3, "rough": (0.78, 0.98), "bump": 0.9},
    # rain water that lies on stone and soaks it dark, without the mirror of standing water
    "water_film": {"kind": "noise", "a": (0.010, 0.014, 0.019), "b": (0.026, 0.033, 0.042),
                   "scale": 5.0, "rough": (0.22, 0.34), "bump": 0.05},
    "valley": {"kind": "noise", "a": (0.01, 0.015, 0.012), "b": (0.03, 0.04, 0.035),
               "scale": 1.0, "rough": (0.9, 1.0), "bump": 0.0},
}


def _obj_coords(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs["Object"]


def _ramp(nt, fac, a, b):
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*a, 1.0)
    ramp.color_ramp.elements[1].color = (*b, 1.0)
    nt.links.new(fac, ramp.inputs["Fac"])
    return ramp.outputs["Color"]


def _map(nt, value, lo, hi):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.inputs["To Min"].default_value = lo
    m.inputs["To Max"].default_value = hi
    nt.links.new(value, m.inputs["Value"])
    return m.outputs["Result"]


def _bump(nt, height, strength, bsdf):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    nt.links.new(height, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def _noise(nt, vec, scale, detail=8.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = 0.6
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def _build_noise(nt, bsdf, s):
    fac = _noise(nt, _obj_coords(nt), s["scale"])
    nt.links.new(_ramp(nt, fac, s["a"], s["b"]), bsdf.inputs["Base Color"])
    nt.links.new(_map(nt, fac, *s["rough"]), bsdf.inputs["Roughness"])
    _bump(nt, fac, s.get("bump", 0.3), bsdf)
    bsdf.inputs["Metallic"].default_value = s.get("metallic", 0.0)


def _build_brick(nt, bsdf, s):
    # walls stand in the XZ and YZ planes, so feed the brick node (x+y, z)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(_obj_coords(nt), sep.inputs[0])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])

    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = s["brick"][0]
    brick.inputs["Row Height"].default_value = s["brick"][1]
    brick.inputs["Mortar Size"].default_value = 0.025
    brick.inputs["Color1"].default_value = (*s["a"], 1.0)
    brick.inputs["Color2"].default_value = (*s["b"], 1.0)
    brick.inputs["Mortar"].default_value = (*s["mortar"], 1.0)
    brick.offset = 0.5
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])

    # grime: large-scale noise darkens the blocks unevenly
    grime = _noise(nt, _obj_coords(nt), 1.5, 6.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    nt.links.new(_map(nt, grime, 0.35, 1.0), mix.inputs["Factor"])
    nt.links.new(brick.outputs["Color"], mix.inputs[6])
    mix.inputs[7].default_value = (0.45, 0.45, 0.48, 1.0)
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    nt.links.new(_map(nt, grime, *s["rough"]), bsdf.inputs["Roughness"])
    # mortar lines recessed: Fac is 1 in the mortar
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], inv.inputs[1])
    _bump(nt, inv.outputs[0], 0.8, bsdf)


def _build_cobble(nt, bsdf, s):
    coords = _obj_coords(nt)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = s["cell"]
    nt.links.new(coords, vor.inputs["Vector"])
    vcol = nt.nodes.new("ShaderNodeTexVoronoi")
    vcol.inputs["Scale"].default_value = s["cell"]
    nt.links.new(coords, vcol.inputs["Vector"])

    # stone color varies per cell, grout where the edge distance is small
    stone = _ramp(nt, vcol.outputs["Distance"], s["a"], s["b"])
    grout_mask = nt.nodes.new("ShaderNodeMapRange")
    grout_mask.inputs["From Min"].default_value = 0.02
    grout_mask.inputs["From Max"].default_value = 0.06
    nt.links.new(vor.outputs["Distance"], grout_mask.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(grout_mask.outputs["Result"], mix.inputs["Factor"])
    mix.inputs[6].default_value = (*s["grout"], 1.0)
    nt.links.new(stone, mix.inputs[7])

    # wet patches: big noise, darker and glossy where wet
    wet = _noise(nt, coords, 0.18, 4.0)
    wet_mask = nt.nodes.new("ShaderNodeMapRange")
    wet_mask.inputs["From Min"].default_value = 0.45
    wet_mask.inputs["From Max"].default_value = 0.58
    nt.links.new(wet, wet_mask.inputs["Value"])
    darken = nt.nodes.new("ShaderNodeMix")
    darken.data_type = "RGBA"
    darken.blend_type = "MULTIPLY"
    nt.links.new(wet_mask.outputs["Result"], darken.inputs["Factor"])
    nt.links.new(mix.outputs[2], darken.inputs[6])
    darken.inputs[7].default_value = (0.45, 0.5, 0.6, 1.0)
    nt.links.new(darken.outputs[2], bsdf.inputs["Base Color"])

    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = s["rough"][1]
    rough.inputs["To Max"].default_value = s["rough"][0]
    nt.links.new(wet_mask.outputs["Result"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    _bump(nt, grout_mask.outputs["Result"], 0.6, bsdf)


def _build_emission(nt, bsdf, s):
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bsdf.inputs["Emission Color"].default_value = (*s["color"], 1.0)
    if s.get("noise"):
        fac = _noise(nt, _obj_coords(nt), 25.0, 4.0)
        nt.links.new(_map(nt, fac, 0.0, s["strength"] * 2), bsdf.inputs["Emission Strength"])
    else:
        bsdf.inputs["Emission Strength"].default_value = s["strength"]


_BUILDERS = {"noise": _build_noise, "brick": _build_brick, "cobble": _build_cobble,
             "emission": _build_emission}


class Materials:
    """Lazy material cache: `mats["iron"]` creates the material on first use.

    A file scene/mats/<key>.py with `def build(mat, nt, bsdf)` replaces the
    SPECS entry for that key, so each material can be developed in its own file.
    """

    def __init__(self):
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            if key not in SPECS:
                raise KeyError(f"unknown material {key!r}; known: {sorted(SPECS)}")
            mat = bpy.data.materials.new(key)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            override = _OVERRIDES / f"{key}.py"
            if override.exists():
                spec = importlib.util.spec_from_file_location(f"mats_{key}", override)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.build(mat, mat.node_tree, bsdf)
            else:
                spec = SPECS[key]
                _BUILDERS[spec["kind"]](mat.node_tree, bsdf, spec)
            self._cache[key] = mat
        return self._cache[key]
