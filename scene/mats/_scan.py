"""Scanned PBR texture sets (Poly Haven, CC0) and the node helpers that map them onto procedural boxes.

The files live in scene/textures/<asset>/{diff,nor_gl,rough,disp}.jpg and come from
scripts/fetch_textures.py. Each image is loaded once per build and shared by every material
that uses it. Missing files raise an error that names the fetch script.

Most meshes are procedural boxes without useful UVs, so the textures are projected from Object
coordinates, which are meters because kit.py keeps object scale at 1:

- `wood()` projects along the three object axes and blends by the face normal (triplanar). On each
  face the texture's grain, which runs along the image's vertical axis, is turned to the longest
  in-plane edge of the object's bounding box. Boards, posts and beams therefore all carry their
  grain lengthwise, whichever local axis they point along.
- `planar()` samples once at a 2D coordinate the caller already has (stone courses, iron straps).

Normal maps are OpenGL convention (green up). A tangent-space normal (r, g, b) becomes
r * T + g * B + b * N, where T and B are the object-space directions in which the image's u and v
grow on that face. That holds whatever the handedness of the projection, so no face is lit
inside out. The result is turned into world space before it reaches the BSDF.
"""

from pathlib import Path

import bpy

TEXTURES = Path(__file__).resolve().parent.parent / "textures"
LUMA = (0.2126, 0.7152, 0.0722)


def image(asset, name):
    """Image datablock for scene/textures/<asset>/<name>.jpg, loaded once and shared."""
    path = TEXTURES / asset / f"{name}.jpg"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run `python3 scripts/fetch_textures.py`")
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if name == "diff" else "Non-Color"
    return img


def _vm(nt, op, *args):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    for i, a in enumerate(args):
        if isinstance(a, bpy.types.NodeSocket):
            nt.links.new(a, n.inputs[i])
        elif a is not None:
            n.inputs[i].default_value = tuple(a) if isinstance(a, (tuple, list)) else (a, a, a)
    return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs["Vector"]


def _math(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        elif v is not None:
            n.inputs[i].default_value = v
    return n.outputs[0]


def _sample(nt, img, uv):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Linear"
    t.extension = "REPEAT"
    nt.links.new(uv, t.inputs["Vector"])
    return t.outputs["Color"]


def _combine(nt, x, y):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, v in enumerate((x, y)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def _decode(nt, color):
    """Normal-map colour (0..1) to a vector in -1..1."""
    return _vm(nt, "MULTIPLY_ADD", color, (2.0, 2.0, 2.0), (-1.0, -1.0, -1.0))


def _tangent_to(nt, nmap, t, b, n):
    """Decoded tangent-space normal `nmap` expressed in the frame (t, b, n)."""
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nmap, sep.inputs[0])
    out = _vm(nt, "SCALE", t, None)
    nt.links.new(sep.outputs[0], out.node.inputs["Scale"])
    for comp, axis in ((sep.outputs[1], b), (sep.outputs[2], n)):
        s = _vm(nt, "SCALE", axis, None)
        nt.links.new(comp, s.node.inputs["Scale"])
        out = _vm(nt, "ADD", out, s)
    return out


def to_world_normal(nt, obj_normal, strength=1.0):
    """Object-space normal to a normalized world normal, blended toward the shading normal by `strength`."""
    vt = nt.nodes.new("ShaderNodeVectorTransform")
    vt.vector_type = "NORMAL"
    vt.convert_from = "OBJECT"
    vt.convert_to = "WORLD"
    nt.links.new(obj_normal, vt.inputs[0])
    n = _vm(nt, "NORMALIZE", vt.outputs[0])
    if strength != 1.0:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "VECTOR"
        mix.inputs[0].default_value = strength
        nt.links.new(geo.outputs["Normal"], mix.inputs[4])
        nt.links.new(n, mix.inputs[5])
        n = _vm(nt, "NORMALIZE", mix.outputs[1])
    return n


def wood(nt, asset, size, across, along, seed, sharp=8.0, maps=("diff", "nor_gl", "rough", "disp")):
    """Triplanar wood with the grain along each face's longest in-plane edge.

    size: per-axis bounding-box size of the object (socket or tuple, meters). across/along: real size of
    one texture tile across and along the grain in meters. seed: per-object random 0..1 (socket);
    it shifts the texture so neighbouring boards differ. sharp: exponent of the face-normal blend.

    Returns a dict with "diff" (colour), "rough" and "disp" (floats, 0..1) and "normal"
    (object-space normal, unnormalized), for the maps requested.
    """
    tc = nt.nodes.new("ShaderNodeTexCoord")
    p, nrm = tc.outputs["Object"], tc.outputs["Normal"]
    sx = nt.nodes.new("ShaderNodeSeparateXYZ")
    if isinstance(size, bpy.types.NodeSocket):
        nt.links.new(size, sx.inputs[0])
    else:
        sx.inputs[0].default_value = size
    sn = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm, sn.inputs[0])
    # blend weights |n|^sharp, normalized
    w_raw = _vm(nt, "POWER", _vm(nt, "ABSOLUTE", nrm), (sharp, sharp, sharp))
    total = _vm(nt, "DOT_PRODUCT", w_raw, (1.0, 1.0, 1.0))
    wsep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(_vm(nt, "DIVIDE", w_raw, _vm(nt, "MAXIMUM", _combine_vec(nt, total), (1e-6, 1e-6, 1e-6))), wsep.inputs[0])

    off_u = _math(nt, "MULTIPLY", seed, 7.31)
    off_v = _math(nt, "MULTIPLY", seed, 13.77)
    axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    # for each projection axis: the two in-plane axes
    planes = ((0, 1, 2), (1, 0, 2), (2, 0, 1))
    acc = {m: None for m in maps}
    for a, b, c in planes:
        # f = 1 when the grain runs along axis b (b is the longer in-plane edge), 0 when along c
        diff_bc = _math(nt, "SUBTRACT", sx.outputs[b], sx.outputs[c])
        f = _math(nt, "MULTIPLY_ADD", diff_bc, 500.0, 0.5)
        f = _math(nt, "MINIMUM", _math(nt, "MAXIMUM", f, 0.0), 1.0)
        mix_along = nt.nodes.new("ShaderNodeMix")
        mix_along.data_type = "VECTOR"
        nt.links.new(f, mix_along.inputs[0])
        mix_along.inputs[4].default_value = axes[c]
        mix_along.inputs[5].default_value = axes[b]
        along_ax = mix_along.outputs[1]
        mix_across = nt.nodes.new("ShaderNodeMix")
        mix_across.data_type = "VECTOR"
        nt.links.new(f, mix_across.inputs[0])
        mix_across.inputs[4].default_value = axes[b]
        mix_across.inputs[5].default_value = axes[c]
        across_ax = mix_across.outputs[1]
        u = _math(nt, "ADD", _math(nt, "DIVIDE", _vm(nt, "DOT_PRODUCT", p, across_ax), across), off_u)
        v = _math(nt, "ADD", _math(nt, "DIVIDE", _vm(nt, "DOT_PRODUCT", p, along_ax), along), off_v)
        # each projection gets its own shift too, so a corner does not mirror the next face
        uv = _combine(nt, _math(nt, "ADD", u, 0.37 * a), _math(nt, "ADD", v, 0.61 * a))
        wa = wsep.outputs[a]
        for m in maps:
            col = _sample(nt, image(asset, m), uv)
            if m == "nor_gl":
                sign = _math(nt, "SIGN", sn.outputs[a])
                n_ax = _vm(nt, "SCALE", axes[a], None)
                nt.links.new(sign, n_ax.node.inputs["Scale"])
                val = _tangent_to(nt, _decode(nt, col), across_ax, along_ax, n_ax)
                term = _vm(nt, "SCALE", val, None)
                nt.links.new(wa, term.node.inputs["Scale"])
                acc[m] = term if acc[m] is None else _vm(nt, "ADD", acc[m], term)
            elif m == "diff":
                term = _vm(nt, "SCALE", col, None)
                nt.links.new(wa, term.node.inputs["Scale"])
                acc[m] = term if acc[m] is None else _vm(nt, "ADD", acc[m], term)
            else:
                term = _math(nt, "MULTIPLY", col, wa)
                acc[m] = term if acc[m] is None else _math(nt, "ADD", acc[m], term)
    out = {"diff": acc.get("diff"), "rough": acc.get("rough"), "disp": acc.get("disp"),
           "normal": acc.get("nor_gl")}
    return out


def _combine_vec(nt, value):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i in range(3):
        nt.links.new(value, n.inputs[i])
    return n.outputs[0]


def luminance(nt, color):
    return _vm(nt, "DOT_PRODUCT", color, LUMA)


def planar(nt, asset, u, v, tile, offset=None, maps=("diff", "nor_gl", "rough", "disp")):
    """One sample of `asset` at (u, v) / tile (+ offset, a socket or number). Returns colour sockets per map."""
    uu = _math(nt, "DIVIDE", u, tile)
    vv = _math(nt, "DIVIDE", v, tile)
    if offset is not None:
        uu = _math(nt, "ADD", uu, offset)
        vv = _math(nt, "ADD", vv, _math(nt, "MULTIPLY", offset, 1.618) if isinstance(offset, bpy.types.NodeSocket) else offset * 1.618)
    uv = _combine(nt, uu, vv)
    return {m: _sample(nt, image(asset, m), uv) for m in maps}


def tangent_normal(nt, color, t, b, n):
    """Normal-map colour in the frame (t, b, n) of vector sockets; returns an unnormalized vector."""
    return _tangent_to(nt, _decode(nt, color), t, b, n)
