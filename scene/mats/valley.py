"""The valley far below the commander's window: wet woods and scrub under mist, seen from above.

The apron of the chamber is a flat skin 9 m under the floor. Crowns of trees are round Voronoi
cells, dark in the gaps and a little lighter at the middle; a second, finer layer breaks them
into leaves. Mist lies on it: with distance along +y the surface fades into a cool grey-blue that
glows faintly, so the far ground meets the sky and the drop has depth. A pale river winds through the valley about 13 m
beyond the back wall: the strip of ground the throat of the window looks at, so the window shows a faint streak of water. Object coordinates are
metres, the box centred on the origin.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

MIST = (0.03, 0.042, 0.07)
RIVER = (0.12, 0.17, 0.26)


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    sx, sy, sz = w.sep(nt, obj)
    crowns = nt.nodes.new("ShaderNodeTexVoronoi")
    crowns.feature = "F1"
    crowns.inputs["Scale"].default_value = 0.42
    nt.links.new(obj, crowns.inputs["Vector"])
    leaf = w.noise(nt, obj, 3.2, 6.0, 0.6)
    crown = w.map_range(nt, crowns.outputs["Distance"], 0.1, 0.75, 1.0, 0.0)
    shade = w.math(nt, "MULTIPLY", crown, w.map_range(nt, leaf, 0.3, 0.7, 0.55, 1.0))
    green = w.ramp(nt, shade, [(0.0, (0.004, 0.006, 0.007)), (0.5, (0.02, 0.034, 0.028)), (1.0, (0.085, 0.11, 0.085))])
    # mist: thin near the cliff foot, thick from about 14 m out
    fog = w.map_range(nt, sy, 4.0, 30.0, 0.04, 0.5)
    patchy = w.map_range(nt, w.noise(nt, obj, 0.07, 3.0, 0.5), 0.35, 0.65, 0.6, 1.15)
    fog = w.math(nt, "MULTIPLY", fog, patchy, clamp=True)
    # a river at the foot of the cliff, reflecting the dusk sky: a meander about 13 m beyond the tower's back wall
    wave = w.math(nt, "ADD", w.math(nt, "MULTIPLY", w.math(nt, "SINE", w.math(nt, "ADD", w.math(nt, "MULTIPLY", sx, 0.28), 0.7)), 2.2),
                  w.math(nt, "MULTIPLY", w.math(nt, "SINE", w.math(nt, "MULTIPLY", sx, 0.77)), 0.7))
    width = w.math(nt, "ADD", 0.3, w.math(nt, "MULTIPLY", w.noise(nt, obj, 0.2, 2.0, 0.5), 0.5))
    off = w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", sy, w.math(nt, "ADD", 12.9, wave)))
    river = w.map_range(nt, w.math(nt, "SUBTRACT", off, width), -0.15, 0.35, 1.0, 0.0)
    river = w.math(nt, "MULTIPLY", river, w.map_range(nt, w.noise(nt, obj, 0.9, 3.0, 0.5), 0.3, 0.6, 0.45, 1.0), clamp=True)
    colour = w.mix_color(nt, fog, green, MIST)
    nt.links.new(colour, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    emit = w.mix_color(nt, river, MIST, RIVER)
    nt.links.new(emit, bsdf.inputs["Emission Color"])
    strength = w.math(nt, "ADD", w.math(nt, "MULTIPLY", w.math(nt, "MULTIPLY", fog, fog), 1.0), w.math(nt, "MULTIPLY", river, 0.12))
    nt.links.new(strength, bsdf.inputs["Emission Strength"])
