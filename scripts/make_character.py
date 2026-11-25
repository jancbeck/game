#!/usr/bin/env python3
"""One command from a character recipe to a game GLB.

    python3 scripts/make_character.py marl                 # characters/marl/recipe.json
    python3 scripts/make_character.py characters/cook/recipe.json --preview

Writes game/assets/characters/<id>.glb and <id>.json (clip metadata: walk period, heel strikes,
step length). `--preview` also renders stills of the rest pose and the walk to
renders/characters/<id>/preview/ with Cycles on the CPU (no GPU queue). `--no-anim` skips the
animation retarget, `--no-export` stops before the GLB.

A new person: copy characters/marl/recipe.json to characters/<id>/recipe.json, change the body
(`macro`: gender, age, muscle, weight, height; `height_m`), the skin, the garment colours and the
beard, run this, then give the person's data/npcs/<id>.json `"model": "<id>"`. Without a `model`
key an NPC keeps the procedural figure.

Needs MPFB, the system asset parts and the CMU clips in characters/vendor/
(`python3 scripts/fetch_character_assets.py`). Blender runs with its user resources inside
characters/vendor/blender, so the user's Blender folders are not touched. Blender with the Metal
GPU needs a session without the Claude Code sandbox.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "characters" / "vendor"
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recipe", help="a character id (characters/<id>/recipe.json) or a recipe path")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-fit", action="store_true", help="skip the cloth shape keys (characters/posefit.py)")
    ap.add_argument("--no-ao", action="store_true", help="skip the baked occlusion")
    ap.add_argument("--show-ao", action="store_true", help="paint the occlusion as the vertex colour (for --sketch)")
    ap.add_argument("--sketch", action="store_true", help="fast Workbench stills of every clip to renders/characters/<id>/sketch/")
    args = ap.parse_args()
    path = Path(args.recipe)
    if not path.suffix:
        path = ROOT / "characters" / args.recipe / "recipe.json"
    if not path.exists():
        sys.exit(f"no recipe at {path}")
    if not (VENDOR / "blender" / "ext" / "user_default" / "mpfb" / "__init__.py").exists():
        sys.exit("MPFB is not installed: run python3 scripts/fetch_character_assets.py")
    env = dict(os.environ)
    env["BLENDER_USER_RESOURCES"] = str(VENDOR / "blender" / "res")
    env["BLENDER_USER_EXTENSIONS"] = str(VENDOR / "blender" / "ext")
    (VENDOR / "blender" / "res").mkdir(parents=True, exist_ok=True)
    cmd = [BLENDER, "--background", "--factory-startup", "--python", str(ROOT / "characters" / "build_human.py"), "--",
           str(path.resolve())]
    cmd += [f"--{name}" for name in ("preview", "no-anim", "no-export", "sketch", "no-fit", "no-ao", "show-ao") if getattr(args, name.replace("-", "_"))]
    result = subprocess.run(cmd, env=env, cwd=ROOT)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
