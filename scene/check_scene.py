"""Build a location's game frame without rendering and check its tables against the built scene.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/check_scene.py -- \
        [--location courtyard]

Part of `scripts/game.py check`. Exits non-zero when:

- a plan entry names a prop module that does not exist (it would build as a magenta box);
- location.json `light_groups` names a source the scene does not have, or two sources share an id;
- a `fires` entry is not an open fire of the scene;
- a hotspot's anchor is missing, or its click volume cannot be computed;
- there are more `perch_names` than crow points in the plan.

It writes the counts of the built scene to renders/check/<location>_scene.json and prints how
they changed since the last check, so a prop that silently disappeared shows up.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import game_frame as gf  # noqa: E402
import location  # noqa: E402
from planlib import entries  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    args = ap.parse_args(argv)
    location.use(args.location)
    t0 = time.time()
    plan, trace, layout, cam = gf.build()
    t_build = time.time() - t0
    srcs, summary = gf.sources()
    probs = []

    missing = sorted(ob.name[len("missing_"):] for ob in bpy.data.objects if ob.name.startswith("missing_"))
    probs += [f"plan: no prop module for {k}" for k in missing]

    ids = [d["id"] for d in srcs]
    probs += [f"light groups: id {i} used by {ids.count(i)} sources" for i in sorted(set(ids)) if ids.count(i) > 1]
    keys = {f"{d['key']}/{[x for x in srcs if x['key'] == d['key']].index(d)}" for d in srcs}
    probs += [f"light_groups: {k} is not a source of the scene" for k, _ in entries(location.table("light_groups"))
              if k not in keys]
    fires = {d["id"] for d in srcs if d["kind"] in gf.FLIPBOOK_KINDS}
    probs += [f"fires: {k} is not an open fire of the scene (open fires: {sorted(fires)})"
              for k, _ in entries(location.table("fires")) if k not in fires]

    hot = location.table("hotspots")
    hids = [h["id"] for h in hot]
    probs += [f"hotspots: id {i} used twice" for i in sorted(set(hids)) if hids.count(i) > 1]
    for h in hot:
        try:
            gf.hotspot_root(h)
        except KeyError:
            probs.append(f"hotspots: {h['id']} anchor {h['anchor']} is not in the scene")
    if not any(p.startswith("hotspots") for p in probs):
        try:
            gf.hotspots()
        except Exception as e:  # noqa: BLE001 - any failure here is a broken table
            probs.append(f"hotspots: click volumes failed: {e!r}")
    names = location.table("perch_names")
    if len(names) > len(plan["crows"].get("points", [])):
        probs.append(f"perch_names: {len(names)} names for {len(plan['crows'].get('points', []))} crow points")

    meshes = [ob for ob in bpy.data.objects if ob.type == "MESH"]
    counts = {"objects": len(bpy.data.objects), "meshes": len(meshes),
              "vertices": sum(len(ob.data.vertices) for ob in meshes),
              "lights": sum(ob.type == "LIGHT" for ob in bpy.data.objects),
              "props": len(entries(plan["props"])) + len(entries(plan["mounted"])),
              "light_groups": len(srcs), "perches": len(gf.bs.PERCHES), "hotspots": len(hot),
              "materials": len(bpy.data.materials)}
    out = ROOT / "renders" / "check" / f"{location.name()}_scene.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        old = json.loads(out.read_text())["counts"]
        diff = {k: f"{old.get(k)} -> {v}" for k, v in counts.items() if old.get(k) != v}
        print(f"CHECK scene changes since the last check: {diff or 'none'}")
    out.write_text(json.dumps({"counts": counts, "build_s": round(t_build, 1), "anim": str(summary)}, indent=1))
    print(f"CHECK scene {location.name()} built in {t_build:.0f}s: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for p in probs:
        print(f"CHECK problem: {p}")
    if probs:
        sys.exit(1)
    print("CHECK ok")


if __name__ == "__main__":
    main()
