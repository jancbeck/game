"""Bake Blender's view transform into a 3D LUT for the Godot runtime.

    Blender --background --factory-startup --python scene/bake_view_lut.py -- \
        [--view AgX] [--look None] [--size 65] [--out game/luts]

The game composites the background layers in linear Rec.709 and then needs the same view
transform Blender used for `reference.png`. This script asks Blender's own OCIO config for
the display/view/look processor and evaluates it on a lattice, so the runtime applies the
exact transform with one 3D texture lookup.

Lattice: each axis samples log2(x / 0.18) evenly from LOG_MIN to LOG_MAX stops, so an input
channel x maps to the coordinate (log2(x / 0.18) - LOG_MIN) / (LOG_MAX - LOG_MIN). The upper
end lies past AgX's own white clip (+4.03 stops), so the inset matrix still sees every value
it can turn into a visible colour.

Output, named by view and look (`agx__none.f32`, `agx__punchy.f32`, ...):
- `<name>.f32`: float32 little-endian RGB, size^3 entries, red fastest, then green, then blue;
  values are display-encoded sRGB in 0..1;
- `<name>.json`: size, LOG_MIN, LOG_MAX, view, look, display.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
import PyOpenColorIO as OCIO

LOG_MIN = -12.5
LOG_MAX = 5.0
MID_GREY = 0.18


def lut_name(view, look):
    slug = lambda s: (s or "none").lower().replace("agx - ", "").replace(" ", "_")
    return f"{slug(view)}__{slug(look)}"


def processor(view="AgX", look=None, display="sRGB"):
    path = Path(bpy.utils.resource_path("LOCAL")) / "datafiles/colormanagement/config.ocio"
    config = OCIO.Config.CreateFromFile(str(path))
    t = OCIO.DisplayViewTransform(src="Linear Rec.709", display=display, view=view)
    if look and look != "None":
        group = OCIO.GroupTransform()
        group.appendTransform(OCIO.LookTransform(src="Linear Rec.709", dst="Linear Rec.709", looks=look))
        group.appendTransform(t)
        t = group
    return config.getProcessor(t).getDefaultCPUProcessor()


def apply(cpu, rgb):
    """Display-encoded values for an (..., 3) array of linear Rec.709 values."""
    flat = np.array(rgb.reshape(-1, 3), dtype=np.float32, order="C", copy=True)
    cpu.applyRGB(flat)
    return flat.reshape(rgb.shape)


def bake(view="AgX", look=None, size=65, out="game/luts"):
    cpu = processor(view, look)
    stops = np.linspace(LOG_MIN, LOG_MAX, size, dtype=np.float64)
    axis = (MID_GREY * 2.0 ** stops).astype(np.float32)
    b, g, r = np.meshgrid(axis, axis, axis, indexing="ij")     # red varies fastest
    lattice = np.stack([r, g, b], axis=-1)
    disp = np.clip(apply(cpu, lattice), 0.0, 1.0).astype("<f4")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    name = lut_name(view, look)
    disp.tofile(out / f"{name}.f32")
    meta = dict(size=size, log_min=LOG_MIN, log_max=LOG_MAX, mid_grey=MID_GREY, view=view,
                look=look, display="sRGB", layout="float32 RGB, red fastest, then green, then blue",
                source=f"Blender {bpy.app.version_string} OCIO config")
    (out / f"{name}.json").write_text(json.dumps(meta, indent=1))
    print(f"baked {out / name}.f32 ({size}^3)")
    return out / f"{name}.f32"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = dict(view="AgX", look=None, size=65, out="game/luts")
    for k, v in zip(argv[::2], argv[1::2]):
        key = k.lstrip("-")
        opts[key] = int(v) if key == "size" else (None if v == "None" else v)
    bake(**opts)


if __name__ == "__main__":
    main()
