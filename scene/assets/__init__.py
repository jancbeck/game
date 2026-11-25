"""Procedural prop modules.

Each module `scene/assets/<name>.py` defines:

    def build(kit, mats, rng) -> bpy.types.Object

It returns a root empty with every part parented under it. Build around the
origin: footprint centered on X/Y = 0, resting on Z = 0, front facing -Y
(toward the camera). Units are meters. Use only `mats[...]` materials from
scene/materials.py and only kit.py helpers or plain bpy/bmesh.

Optional module constant:

    LIGHTS = [((x, y, z), (r, g, b), watts), ...]   # point lights, root-relative

build_scene.py places, rotates and scales the root from layout.json.
"""

import importlib
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def available():
    return sorted(p.stem for p in _DIR.glob("*.py") if not p.stem.startswith("_"))


def load(name):
    return importlib.import_module(f"assets.{name}")
