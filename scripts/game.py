#!/usr/bin/env python3
"""One entry point for building, rendering, exporting and checking a location.

    scripts/game.py check   [--location courtyard] [--no-build]     # about a minute, no GPU; the courtyard run also plays the whole quest
    scripts/game.py preview [--view ref|eye|plan] [--percent 50] [--check-scale]   # EEVEE still
    scripts/game.py draft   [step ...] [--full-frame] [--all-tiles] [--to-game]   # every step at reduced quality, into renders/draft/
    scripts/game.py final   [step ...]          # the full game export; only stale steps run
    scripts/game.py status  [--tier final]      # which steps are stale, and why
    scripts/game.py adopt                       # take the game/ export as current (see below)

Tiers. `preview` renders one EEVEE still of the location (renders/preview/). `draft` runs the
game-export steps at low samples or reduced size into renders/draft/<location>/, laid out like
game/. `final` runs them at full quality into game/ (location.game_dir()). The steps, in order:
layers, ids, wide, tiles, flipbooks, fire, lut, export (the game-export skill).

A draft is a quarter of the frame by default, which is enough to look at. `--full-frame` renders the whole
2560 x 1440 frame at the draft's samples, so the export validates, `--all-tiles` renders the tile of every hotspot (the draft
renders the first one only), and `--to-game` writes the draft into
the location's game folder (game/ for the first location, game/locations/<name>/ for the others), where the
stamps mark it as a draft: `final` renders those steps again.

Staleness. Each step hashes its inputs (code without comments and docstrings, location files
without `_doc` keys): the scene code and assets it runs, the location files and
tables it reads, its own arguments and the Blender version. The hash is written to
<out>/build/steps/<step>.json when the step succeeds. A step whose hash is unchanged and whose
outputs exist is skipped (--force runs it anyway); `status` names the files that changed.

Adopt. `adopt` writes the stamps of the final steps for the inputs as they are now, without
running anything, so a checkout whose game/ export is known to match its sources does not render
again. When a render step's build/*.json is missing, it is rebuilt from data/scene.json first.

GPU. Every Blender run that renders goes through scripts/gpu.py, one at a time on this machine.
Before each one the estimate from earlier runs is printed. Each step's time is also appended to
the repository's timings.csv.
"""

import argparse
import ast
import hashlib
import json
import os
import plistlib
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = "courtyard"            # the first location: its export lives in game/ itself
sys.path.insert(0, str(ROOT / "scripts"))
import gpu  # noqa: E402

BLENDER = Path(os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender"))
GODOT = Path(os.environ.get("GODOT", "/Applications/Godot.app/Contents/MacOS/Godot"))
SCENE = ROOT / "scene"

# scene/ files that are entry points of one step; every other scene/*.py builds the scene for all
STEP_SCRIPTS = {"game_layers.py", "game_flipbooks.py", "game_fire.py", "game_views.py", "export_game.py",
                "game_walk.py", "game_fire_check.py", "bake_view_lut.py", "check_scene.py", "render_orbit.py",
                "descent.py", "orbit_audio.py", "prop_preview.py"}
LOCATION_FILES = ("plan.json", "trace.json", "layout.json")
# location.json tables the scene build reads, and hotspot fields that change pictures (not texts)
BUILD_TABLES = ("light_groups",)
HOTSPOT_GEOMETRY = ("hotspots", ("id", "anchor", "stand", "volume", "min_h"))

# A step: its Blender runs (script, args by tier, whether it renders), extra inputs and outputs.
# `est`: seconds on the M1 Pro, used until the queue has timings of its own.
STEPS = {
    "layers": dict(runs=[("game_layers.py", {"final": [], "draft": ["--percent", "25", "--samples", "16"]}, True)],
                   code=["game_layers.py"], outputs=["build/layers.json", "assets/layers/base.exr"],
                   est={"final": 2100, "draft": 150}),
    "ids": dict(runs=[("game_views.py", {"final": ["--view", "ids"], "draft": ["--view", "ids", "--data-samples", "2"]},
                       True)],
                code=["game_views.py", "game_layers.py"], tables=[HOTSPOT_GEOMETRY],
                outputs=["build/view_ids.json", "assets/masks/ids.png"], est={"final": 180, "draft": 120}),
    "wide": dict(runs=[("game_views.py", {"final": ["--view", "wide", "--samples", "64"],
                                          "draft": ["--view", "wide", "--samples", "8", "--data-samples", "2"]}, True)],
                 code=["game_views.py", "game_layers.py"], tables=[HOTSPOT_GEOMETRY],
                 outputs=["build/view_wide.json", "assets/wide/base.exr"], est={"final": 960, "draft": 240}),
    "tiles": dict(runs=[("game_views.py", {"final": ["--view", "tiles", "--samples", "80"],
                                           "draft": ["--view", "tiles", "--samples", "8", "--data-samples", "2",
                                                     "--only", "{first_hotspot}"]}, True)],
                  code=["game_views.py", "game_layers.py"], tables=[HOTSPOT_GEOMETRY],
                  outputs=["build/view_tiles.json"], est={"final": 3360, "draft": 300}),
    "flipbooks": dict(runs=[("game_flipbooks.py", {"final": [], "draft": ["--frames", "6"]}, True)],
                      code=["game_flipbooks.py", "game_layers.py"], files=["layout_preview.json"],
                      outputs=["build/flipbooks.json"], est={"final": 180, "draft": 120}),
    # the simulations bake on the CPU outside the queue; only the render holds the GPU
    "fire": dict(runs=[("game_fire.py", {"final": ["--bake-only", "--reuse"], "draft": ["--quick", "--bake-only", "--reuse"]},
                        False),
                       ("game_fire.py", {"final": ["--reuse"], "draft": ["--quick", "--reuse"]}, True)],
                 code=["game_fire.py", "game_flipbooks.py", "game_layers.py"], tables=["fires"],
                 outputs=["build/fire_flipbooks.json"], est={"final": 420, "draft": 180}),
    "lut": dict(runs=[("bake_view_lut.py", {"final": ["--look", "AgX - Punchy"], "draft": ["--look", "AgX - Punchy"]},
                       False)],
                code=["bake_view_lut.py"], shared=False, outputs=["luts/agx__punchy.f32"], est={"final": 20, "draft": 20}),
    "export": dict(runs=[("export_game.py", {"final": [], "draft": []}, False)],
                   code=["export_game.py", "game_walk.py"], tables=["perch_names", "hotspots", "exits", "people"],
                   after=["layers", "ids", "wide", "tiles", "flipbooks", "fire"],
                   audio=["rain_bed_t1_loop.wav", "brazier_t1_loop.wav"],
                   outputs=["data/scene.json", "data/hotspots.json"], est={"final": 100, "draft": 100}),
}
ORDER = list(STEPS)
TIERS = ("draft", "final")
SHARED_STEPS = ("lut",)         # written once into game/luts, not per location
FULL_FRAME = False              # draft arguments render the whole frame (set by --full-frame)
ALL_TILES = False               # the draft tiles step renders every hotspot, not only the first (--all-tiles)


def tier_args(args, tier, loc):
    """The arguments of a step's run for a tier: `{first_hotspot}` is the location's first hotspot, and a
    full-frame draft renders 100 percent instead of 25, and an all-tiles draft renders every hotspot's tile."""
    out = list(args[tier])
    if "{first_hotspot}" in out:
        first = json.loads((ROOT / "locations" / loc / "location.json").read_text())["hotspots"][0]["id"]
        out = [first if a == "{first_hotspot}" else a for a in out]
    if FULL_FRAME and tier == "draft" and "--percent" in out:
        out[out.index("--percent") + 1] = "100"
    if ALL_TILES and tier == "draft" and "--only" in out:
        del out[out.index("--only"):out.index("--only") + 2]
    return out


# ---------- inputs ----------

def sha(data):
    return hashlib.sha1(data).hexdigest()[:16]


def _strip_docs(o):
    if isinstance(o, dict):
        return {k: _strip_docs(v) for k, v in o.items() if not k.startswith("_doc") and k != "note"}
    if isinstance(o, list):
        return [_strip_docs(v) for v in o]
    return o


def _code(src):
    """Python source without comments and docstrings, as its syntax tree."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree).encode()


def file_hashes(paths):
    """{path: hash}. Python files are hashed without comments and docstrings, a location's JSON
    files without their `_doc` keys and notes, so editing a description does not make a render
    stale."""
    out = {}
    for p in sorted(paths):
        if not p.is_file():
            continue
        st = p.stat()
        key = (p, st.st_mtime_ns, st.st_size)
        if key in _HASHED:
            out[str(p.relative_to(ROOT))] = _HASHED[key]
            continue
        data = p.read_bytes()
        if p.suffix == ".json" and p.parent.parent.name == "locations":
            data = json.dumps(_strip_docs(json.loads(data)), sort_keys=True).encode()
        elif p.suffix == ".py":
            try:
                data = _code(data)
            except SyntaxError:
                pass
        out[str(p.relative_to(ROOT))] = _HASHED[key] = sha(data)
    return out


_HASHED = {}


def scene_inputs():
    """Every file the scene build reads: shared scene code, assets, material recipes, textures."""
    files = [p for p in SCENE.glob("*.py") if p.name not in STEP_SCRIPTS]
    for sub in ("assets", "mats", "textures"):
        files += [p for p in (SCENE / sub).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and not any(part.startswith(".") for part in p.relative_to(SCENE).parts)]
    return files


def blender_version():
    plist = BLENDER.parent.parent / "Info.plist"
    try:
        return plistlib.loads(plist.read_bytes()).get("CFBundleVersion", "?")
    except (OSError, ValueError):
        return "?"


def table_hash(loc, spec):
    data = json.loads((ROOT / "locations" / loc / "location.json").read_text())
    if isinstance(spec, tuple):
        key, fields = spec
        value = [{k: v for k, v in h.items() if k in fields} for h in data.get(key, [])]
    else:
        key, value = spec, data.get(spec)
    return f"location.json:{key}", sha(json.dumps(_strip_docs(value), sort_keys=True).encode())


def step_inputs(step, tier, loc, out):
    """{input name: hash} of one step."""
    s = STEPS[step]
    inputs = {}
    if s.get("shared", True):
        inputs.update(file_hashes(scene_inputs()))
        inputs.update(file_hashes([ROOT / "locations" / loc / f for f in LOCATION_FILES]))
        for t in BUILD_TABLES:
            k, v = table_hash(loc, t)
            inputs[k] = v
    inputs.update(file_hashes([SCENE / f for f in s["code"]]))
    inputs.update(file_hashes([ROOT / "locations" / loc / f for f in s.get("files", [])]))
    for t in s.get("tables", []):
        k, v = table_hash(loc, t)
        inputs[k] = v
    for a in s.get("audio", []):
        inputs.update(file_hashes([ROOT / "audio" / "sfx" / "stable-audio-3" / "norm" / a]))
    for dep in s.get("after", []):
        for o in STEPS[dep]["outputs"]:
            p = out / o
            if p.suffix == ".json" and p.exists():
                inputs[f"{dep}:{o}"] = sha(p.read_bytes())
    inputs["args"] = sha(json.dumps([tier_args(r[1], tier, loc) for r in s["runs"]]).encode())
    inputs["blender"] = blender_version()
    return inputs


def digest(inputs):
    return sha(json.dumps(inputs, sort_keys=True).encode())


def out_dir(tier, loc):
    if tier == "final":
        sys.path.insert(0, str(SCENE))
        import location
        location.use(loc)
        return location.game_dir()
    return ROOT / "renders" / "draft" / loc


def stamp_path(out, step):
    return out / "build" / "steps" / f"{step}.json"


def staleness(step, tier, loc, out):
    """(stale?, reason, inputs)."""
    inputs = step_inputs(step, tier, loc, out)
    missing = [o for o in STEPS[step]["outputs"] if not (out / o).exists()]
    sp = stamp_path(out, step)
    if not sp.exists():
        return True, "never run" + (f" (missing {missing[0]})" if missing else ""), inputs
    old = json.loads(sp.read_text())
    if missing:
        return True, f"missing {missing[0]}", inputs
    if old.get("hash") == digest(inputs):
        return False, f"up to date ({old.get('finished', '?')})", inputs
    changed = sorted(k for k in set(inputs) | set(old.get("inputs", {}))
                     if inputs.get(k) != old.get("inputs", {}).get(k))
    more = f" and {len(changed) - 4} more" if len(changed) > 4 else ""
    return True, "changed: " + ", ".join(changed[:4]) + more, inputs


# ---------- running ----------

def log_timing(name, est, actual):
    with (ROOT / "timings.csv").open("a") as f:
        f.write(f"game,{name},{'' if est is None else round(est)},{round(actual)},"
                f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\n")


def blender_cmd(script, args, loc, out=None):
    cmd = [str(BLENDER), "--background"]
    if script == "bake_view_lut.py":
        cmd.append("--factory-startup")
    cmd += ["--python-exit-code", "1", "--python", str(SCENE / script), "--"]
    if script == "bake_view_lut.py":
        return cmd + args + ["--out", str(out / "luts")]
    return cmd + ["--location", loc] + args + (["--out", str(out)] if out else [])


def run_job(name, cmd, render, default_est, log):
    """Run one Blender job (through the GPU queue when it renders), its output to `log`; returns
    (exit code, seconds). On failure the end of the log is printed."""
    est = gpu.estimate(name) or default_est
    source = "from earlier runs" if gpu.estimate(name) else "default"
    log.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    if render:
        print(f"== {name}: GPU job, estimate {gpu._fmt_s(est)} ({source}), log {log}", flush=True)
        code = gpu.run(name, cmd, est, cwd=ROOT, log=log)
    else:
        print(f"== {name}: CPU job, estimate {gpu._fmt_s(est)} ({source}), log {log}", flush=True)
        with log.open("w") as f:
            code = subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        gpu._log({"name": name, "start": gpu._stamp(t), "end": gpu._stamp(time.time()),
                  "seconds": round(time.time() - t, 1), "exit": code, "estimate_s": round(est) if est else "",
                  "cwd": str(ROOT), "cmd": " ".join(cmd)})
    dt = time.time() - t
    log_timing(name, est, dt)
    if code != 0:
        print("".join(log.read_text(errors="replace").splitlines(keepends=True)[-30:]))
    return code, dt


def run_steps(tier, steps, loc, force=False, to_game=False):
    out = out_dir("final", loc) if to_game else out_dir(tier, loc)
    steps = steps or [x for x in ORDER if loc == DEFAULT or x not in SHARED_STEPS]
    unknown = [s for s in steps if s not in STEPS]
    if unknown:
        sys.exit(f"unknown steps {unknown}; steps are {ORDER}")
    t0, ran = time.time(), []
    for step in [s for s in ORDER if s in steps]:
        stale, why, inputs = staleness(step, tier, loc, out)
        if not stale and not force:
            print(f"-- {tier}/{step}: {why}, skipped", flush=True)
            continue
        print(f"-- {tier}/{step}: {why}", flush=True)
        total = 0.0
        for script, args, render in STEPS[step]["runs"]:
            name = f"{loc}/{tier}/{step}" + ("" if render or len(STEPS[step]["runs"]) == 1 else "-cpu")
            share = STEPS[step]["est"][tier] if render or len(STEPS[step]["runs"]) == 1 else None
            log = out / "build" / "logs" / f"{name.rsplit('/', 1)[-1]}.log"
            code, dt = run_job(name, blender_cmd(script, tier_args(args, tier, loc), loc, out), render, share, log)
            total += dt
            if code != 0:
                sys.exit(f"{tier}/{step} failed (exit {code}); later steps not run")
        inputs = step_inputs(step, tier, loc, out)        # outputs of earlier steps may have changed
        stamp_path(out, step).parent.mkdir(parents=True, exist_ok=True)
        stamp_path(out, step).write_text(json.dumps({"hash": digest(inputs), "inputs": inputs, "tier": tier,
                                                     "location": loc, "seconds": round(total),
                                                     "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1))
        ran.append((step, total))
    print(f"{tier} done in {gpu._fmt_s(time.time() - t0)}: "
          + (", ".join(f"{s} {gpu._fmt_s(t)}" for s, t in ran) or "nothing was stale") + f"; output in {out}")


def rebuild_build_json(out):
    """build/*.json of the render steps from data/scene.json, for those that are missing."""
    s = json.loads((out / "data" / "scene.json").read_text())
    b = out / "build"
    b.mkdir(parents=True, exist_ok=True)
    made = []

    def write(name, data):
        if not (b / name).exists():
            (b / name).write_text(json.dumps(data, indent=1))
            made.append(name)
    lay = dict(s["layers"], depth=s["depth"], checks=s["checks"]["layers"], mask_stats=s["checks"]["mask_stats"],
               render=s["checks"]["render"])
    lay["groups"] = [dict({k: v for k, v in g.items() if k != "anchor"},
                          anchor_blender=[g["anchor"][0], -g["anchor"][2], g["anchor"][1]]) for g in s["layers"]["groups"]]
    write("layers.json", lay)
    write("flipbooks.json", {f["id"]: f for f in s["flipbooks"] if f.get("source") != "mantaflow"})
    write("fire_flipbooks.json", {f["id"]: f for f in s["flipbooks"] if f.get("source") == "mantaflow"})
    if "ids" in s["masks"]:
        write("view_ids.json", {"ids": s["masks"]["ids"]})
    v, cv = s.get("views", {}), s["checks"].get("views", {})
    if "wide" in v:
        w = v["wide"]
        write("view_wide.json", {"camera": w["camera"], "base": w["base"], "groups": w["groups"], "depth": w["depth_meta"],
                                 "ids": w["ids"], "masks": w["masks"], "reference": w["reference"],
                                 **cv.get("wide", {})})
    if "tiles" in v:
        per = cv.get("tiles", {}).get("per_tile", {})
        write("view_tiles.json", {"tiles": [dict(t, **per.get(t["id"], {})) for t in v["tiles"]],
                                  "render": cv.get("tiles", {}).get("render", {})})
    return made


def adopt(loc):
    out = out_dir("final", loc)
    made = rebuild_build_json(out)
    if made:
        print(f"rebuilt from data/scene.json: {', '.join(made)}")
    for step in ORDER:
        missing = [o for o in STEPS[step]["outputs"] if not (out / o).exists()]
        if missing:
            print(f"  {step}: not adopted, missing {missing[0]}")
            continue
        inputs = step_inputs(step, "final", loc, out)
        stamp_path(out, step).parent.mkdir(parents=True, exist_ok=True)
        stamp_path(out, step).write_text(json.dumps({"hash": digest(inputs), "inputs": inputs, "tier": "final",
                                                     "location": loc, "adopted": True,
                                                     "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1))
        print(f"  {step}: adopted")


def status(tier, loc):
    out = out_dir(tier, loc)
    print(f"{tier} ({out}):")
    for step in ORDER:
        if loc != DEFAULT and step in SHARED_STEPS:
            continue
        stale, why, _ = staleness(step, tier, loc, out)
        est = gpu.estimate(f"{loc}/{tier}/{step}") or STEPS[step]["est"][tier]
        print(f"  {step:<10} {'STALE' if stale else 'ok   '}  ~{gpu._fmt_s(est):>9}  {why}")


def preview(loc, view, percent, check_scale, force):
    """EEVEE stills of one or more views (`view` is comma-separated). Views whose inputs did not change are
    kept; the others are rendered from one scene build."""
    names = view.split(",")
    folder = ROOT / "renders" / "preview"
    inputs = file_hashes(scene_inputs() + [SCENE / "build_scene.py"]
                         + [ROOT / "locations" / loc / f for f in ("plan.json", "trace.json", "layout_preview.json",
                                                                   "layout.json", "location.json")])
    stale = []
    for name in names:
        out = folder / f"{loc}_{name}{'_scale' if check_scale else ''}.png"
        inputs["args"] = f"{name} {percent} {check_scale} {blender_version()}"
        sp = out.with_suffix(".json")
        if out.exists() and sp.exists() and json.loads(sp.read_text()).get("hash") == digest(inputs) and not force:
            print(f"preview up to date: {out}")
        else:
            stale.append((name, out, sp, digest(inputs)))
    if not stale:
        return
    folder.mkdir(parents=True, exist_ok=True)
    cmd = [str(BLENDER), "--background", "--python-exit-code", "1", "--python", str(SCENE / "build_scene.py"), "--",
           "--location", loc, "--layout", str(ROOT / "locations" / loc / "layout_preview.json"),
           "--percent", str(percent), "--view", ",".join(n for n, *_ in stale),
           "--out", str(folder if len(stale) > 1 else stale[0][1])] + (["--check-scale"] if check_scale else [])
    code, dt = run_job(f"{loc}/preview/{'+'.join(n for n, *_ in stale)}@{percent}", cmd, True,
                       70 + len(stale) * 60 * (percent / 100) ** 2, folder / f"{loc}_{stale[0][0]}.log")
    if code:
        sys.exit(f"preview failed (exit {code})")
    for name, out, sp, h in stale:
        sp.write_text(json.dumps({"hash": h, "seconds": round(dt / len(stale))}))
        print(f"preview -> {out}")
    print(f"preview took {gpu._fmt_s(dt)}")


# ---------- check ----------

IGNORED_GODOT = ("Failed to open 'user://logs", "Failed to open log file", "get_system_ca_certificates",
                 'Condition "ret != noErr" is true', "ObjectDB instances were leaked", "at: cleanup")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def validate_skill_tags(game, src):
    """Problems in the skill, check and journal tags of the Ink source: unknown skills, difficulties that
    are neither a number nor a name of data/skills.json, and a journal task that is closed but never opened."""
    probs = []
    path = game / "data/skills.json"
    if not path.exists():
        return probs
    doc = json.loads(path.read_text())
    ids = {k["id"] for k in doc["skills"]}
    levels = {d["name"].lower() for d in doc["difficulties"]}

    def skill(name, where):
        if name not in ids:
            probs.append(f"story: {where}: no skill '{name}' in data/skills.json")

    def level(value, where):
        if not (value.isdigit() or value.lower() in levels):
            probs.append(f"story: {where}: difficulty '{value}' is not a number or a name of data/skills.json")

    for m in re.finditer(r"#\s*skill:\s*(\w+)", src):
        skill(m.group(1), "# skill")
    for m in re.finditer(r"#\s*passive:\s*(\w+)", src):
        level(m.group(1), "# passive")
    for m in re.finditer(r"#\s*check:\s*([^\]\n#]+)", src):
        f = [x.strip() for x in m.group(1).split(":")]
        where = f"#check:{m.group(1).strip()}"
        skill(f[0], where)
        level(f[1] if len(f) > 1 else "", where)
        if len(f) > 2 and f[2] not in ("white", "red"):
            probs.append(f"story: {where}: the kind is white or red, not '{f[2]}'")
    for m in re.finditer(r'\broll\(\s*"(\w+)"\s*,\s*"?(\w+)"?\s*,\s*"(\w+)"', src):
        where = f"roll({m.group(1)}, {m.group(2)}, {m.group(3)})"
        skill(m.group(1), where)
        level(m.group(2), where)
        if m.group(3) not in ("white", "red"):
            probs.append(f"story: {where}: the kind is white or red")
    opened = set(re.findall(r"#\s*journal:\s*(\w+):", src))
    for task in sorted(set(re.findall(r"#\s*journal_done:\s*(\w+)", src)) - opened):
        probs.append(f"story: journal task '{task}' is closed but no line opens it with # journal:{task}:<text>")
    return probs


def validate_chapters(game, src):
    """Problems in data/chapters.json against the story: every chapter the story ends with end_chapter(\"<id>\")
    exists, has a title, and its summary rows read story variables that the story declares with VAR."""
    probs = []
    cfg = json.loads((game / "config.json").read_text())
    path = game / cfg.get("chapters", "data/chapters.json")
    ids = set(re.findall(r'\bend_chapter\(\s*"([^"]+)"', src)) - {"id"}
    if not path.exists():
        return [f"chapters: missing {path.relative_to(game)}"] if ids else []
    chapters = json.loads(path.read_text()).get("chapters", {})
    declared = set(re.findall(r"^VAR\s+(\w+)", src, re.M))
    for cid in sorted(ids - set(chapters)):
        probs.append(f"chapters: the story ends chapter '{cid}', which data/chapters.json does not have")
    for cid, ch in chapters.items():
        if not ch.get("title"):
            probs.append(f"chapters.{cid}: no title")
        for row in ch.get("summary", {}).get("lines", []):
            if row.get("var") not in declared:
                probs.append(f"chapters.{cid}: the row '{row.get('label')}' reads '{row.get('var')}', which the story does not declare with VAR")
            if not row.get("label") or not isinstance(row.get("values", {}), dict):
                probs.append(f"chapters.{cid}: a row needs a label and a values object: {row}")
    return probs


def validate_story(game):
    """Problems in the Ink story and what it names: items, hotspots, people, chapters, a stale main.json."""
    probs = []
    story = game / "data/story"
    if not (story / "main.ink").exists():
        return probs
    src = "\n".join(p.read_text() for p in sorted(story.glob("*.ink")))
    item_file = game / "data/items.json"
    items = {i["id"] for i in json.loads(item_file.read_text()).get("items", [])} if item_file.exists() else set()
    for m in re.finditer(r'(?:give_item|take_item|has_item)\(\s*"([^"]+)"', src):
        if m.group(1) not in items:
            probs.append(f"story: item '{m.group(1)}' is not in data/items.json")
    hotspots = set()
    for path in [game / "data/hotspots.json", *sorted(game.glob("locations/*/data/hotspots.json"))]:
        if path.exists():
            hotspots |= {h["id"] for h in json.loads(path.read_text())}
    knots = set(re.findall(r"^===\s*(?:function\s+)?(\w+)\s*=*\s*$", src, re.M))
    for k in sorted(knots):
        if k.startswith("look_") and k[5:] not in hotspots:
            probs.append(f"story: knot {k} is for a hotspot that no location has")
    for npc in sorted((game / "data/npcs").glob("*.json")):
        d = json.loads(npc.read_text())
        if d.get("knot", f"talk_{d['id']}") not in knots:
            probs.append(f"story: no knot {d.get('knot', 'talk_' + d['id'])} for {npc.name}")
    probs += validate_skill_tags(game, src)
    probs += validate_chapters(game, src)
    if not (story / "main.json").exists():
        probs.append("story: main.json is missing; run scripts/ink.py")
    else:
        import ink
        probs += ink.stale()
    return probs


def data_path(loc):
    """scene.json of a location, relative to game/."""
    return "data/scene.json" if loc == DEFAULT else f"locations/{loc}/data/scene.json"


def validate_game(game, loc=DEFAULT):
    """Problems in the game data of a location against the data contract (the game-export skill): files, ids,
    rects. `game` is the game/ folder, which every path in scene.json is relative to."""
    probs = []
    cfg = json.loads((game / "config.json").read_text())
    scene_path = game / data_path(loc)
    s = json.loads(scene_path.read_text())
    hot = json.loads((scene_path.parent / "hotspots.json").read_text())
    W, H = s["camera"]["resolution"]

    def need(rel, what):
        if rel and not (game / rel).exists():
            probs.append(f"{what}: missing file {rel}")

    def unique(ids, what):
        seen = set()
        for i in ids:
            if i in seen:
                probs.append(f"{what}: duplicate id {i}")
            seen.add(i)

    def rect_in(r, w, h, what):
        x, y, rw, rh = r
        if x < 0 or y < 0 or rw <= 0 or rh <= 0 or x + rw > w or y + rh > h:
            probs.append(f"{what}: rect {r} outside the {w}x{h} frame")

    def f32(meta, what):
        p = game / meta["file"]
        if p.exists() and p.stat().st_size != meta["width"] * meta["height"] * 4:
            probs.append(f"{what}: {meta['file']} is {p.stat().st_size} bytes, not {meta['width']}x{meta['height']}x4")

    need(s["depth"]["file"], "depth")
    f32(s["depth"], "depth")
    L = s["layers"]
    for k in ("base", "reference", "reference_post"):
        need(L.get(k), f"layers.{k}")
    unique([g["id"] for g in L["groups"]], "layers.groups")
    for g in L["groups"]:
        need(g["image"], f"layers.groups.{g['id']}")
        if g["curve"] not in ("fire", "interior", "lamp", "banked"):
            probs.append(f"layers.groups.{g['id']}: unknown curve {g['curve']}")
    group_ids = {g["id"] for g in L["groups"]}
    for k, v in s["masks"].items():
        if not k.startswith("_"):
            need(v, f"masks.{k}")
            if (game / v).exists() and png_size(game / v) not in (None, (W, H)):
                probs.append(f"masks.{k}: {v} is {png_size(game / v)}, not {W}x{H}")
    views = s.get("views", {})
    if "wide" in views:
        w = views["wide"]
        for k in ("base", "depth", "ids", "reference"):
            need(w[k], f"views.wide.{k}")
        for g in w["groups"]:
            need(g["image"], f"views.wide.groups.{g['id']}")
    tiles = views.get("tiles", [])
    unique([t["id"] for t in tiles], "views.tiles")
    hot_ids = [h["id"] for h in hot]
    for t in tiles:
        rect_in(t["rect"], W, H, f"views.tiles.{t['id']}")
        if t["hotspot"] not in hot_ids:
            probs.append(f"views.tiles.{t['id']}: unknown hotspot {t['hotspot']}")
        for k in ("base", "depth", "ids", "reference"):
            need(t[k], f"views.tiles.{t['id']}.{k}")
        for k, v in t.get("masks", {}).items():
            need(v, f"views.tiles.{t['id']}.masks.{k}")
        for g in t["groups"]:
            need(g["image"], f"views.tiles.{t['id']}.groups.{g['id']}")
            if g["id"] not in group_ids:
                probs.append(f"views.tiles.{t['id']}: group {g['id']} is not a main-frame group")
    unique([f["id"] for f in s["flipbooks"]], "flipbooks")
    for f in s["flipbooks"]:
        need(f["atlas"], f"flipbooks.{f['id']}")
        rect_in(f["rect"], W, H, f"flipbooks.{f['id']}")
        if f.get("group") and f["group"] not in group_ids:
            probs.append(f"flipbooks.{f['id']}: unknown group {f['group']}")
        size = png_size(game / f["atlas"]) if (game / f["atlas"]).exists() else None
        if size and "cell" in f and (size[0] < f["cols"] * f["cell"][0] or size[1] < f["rows"] * f["cell"][1]):
            probs.append(f"flipbooks.{f['id']}: atlas {size} smaller than {f['cols']}x{f['rows']} cells of {f['cell']}")
        if f["frames"] > f["cols"] * f["rows"]:
            probs.append(f"flipbooks.{f['id']}: {f['frames']} frames in {f['cols']}x{f['rows']} cells")
        if f["id"].endswith("@2") and f["id"][:-2] not in {x["id"] for x in s["flipbooks"]}:
            probs.append(f"flipbooks.{f['id']}: no 1x entry {f['id'][:-2]}")
    c = s["crows"]
    need(c["model"], "crows.model")
    unique([p["id"] for p in c["perches"]], "crows.perches")
    perch_ids = {p["id"] for p in c["perches"]}
    probs += [f"crows.start: unknown perch {p}" for p in c["start"] if p not in perch_ids]
    wk = s["walk"]
    need(wk["mesh"], "walk.mesh")
    need(s.get("proxy"), "proxy")
    unique([e["id"] for e in wk["exits"]], "walk.exits")
    unique([p["id"] for p in wk.get("portals", [])], "walk.portals")
    unique([li["name"] for li in s["lights"]], "lights")
    probs += [f"lights.{li['name']}: unknown group {li['group']}" for li in s["lights"]
              if li.get("group") not in group_ids | {"base"}]
    unique(hot_ids, "hotspots")
    for h in hot:
        for k in ("id", "name", "text", "volume", "stand", "screen_px"):
            if k not in h:
                probs.append(f"hotspots.{h.get('id')}: no {k}")
        if "screen_px" in h:
            x, y = h["screen_px"]
            if not (0 <= x <= W and 0 <= y <= H):
                probs.append(f"hotspots.{h['id']}: stand point {h['screen_px']} outside the frame")
    snd_path = game / cfg.get("sounds", "data/sounds.json")
    if snd_path.exists():
        snd = json.loads(snd_path.read_text())

        def files(v, where):
            if isinstance(v, str) and v.endswith((".wav", ".ogg", ".mp3")):
                need(v, f"sounds{where}")
            elif isinstance(v, dict):
                for k, x in v.items():
                    files(x, f"{where}.{k}")
            elif isinstance(v, list):
                for x in v:
                    files(x, where)
        files(snd, "")
        for surf in wk.get("surfaces", []):
            if surf not in snd.get("footsteps", {}):
                probs.append(f"sounds.footsteps: no clips for surface {surf}")
        for p in wk.get("portals", []):
            if p.get("sound") and p["sound"] not in snd.get("portals", {}):
                probs.append(f"sounds.portals: no sound {p['sound']} for portal {p['id']}")
        if loc == DEFAULT:
            probs += [f"sounds.hotspots: unknown hotspot {k}" for k in snd.get("hotspots", {})
                      if not k.startswith("_") and k not in hot_ids]
    else:
        probs.append(f"sounds: missing {snd_path.relative_to(game)}")
    if loc == DEFAULT:
        for k in ("rain", "fire"):
            need(cfg.get("audio", {}).get(k), f"config.audio.{k}")
        for v in cfg.get("audio", {}).get("crows", []):
            need(v, "config.audio.crows")
    summary = (f"{len(L['groups'])} light groups, {len(tiles)} tiles, {len(s['flipbooks'])} flipbooks, "
               f"{len(c['perches'])} perches, {len(s['lights'])} lights, {len(hot)} hotspots")
    probs += validate_story(game)
    return probs, summary


def godot_smoke(game, data=None):
    """Run the game headless for a few seconds, on `data` (a scene.json relative to game/) when given;
    returns (problems, summary line)."""
    if not GODOT.exists():
        return [f"Godot not found at {GODOT}"], ""
    try:
        # the Ink runtime registers global classes, which Godot learns from an import scan
        subprocess.run([str(GODOT), "--headless", "--path", str(game), "--import"], capture_output=True, timeout=300)
        r = subprocess.run([str(GODOT), "--headless", "--path", str(game), "--script", "res://scripts/smoke.gd"]
                           + (["--", f"--data={data}"] if data else []),
                           capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return ["Godot smoke run timed out after 300 s"], ""
    lines = (r.stdout + r.stderr).splitlines()
    errors = [ln for ln in lines if re.search(r"SCRIPT ERROR|^ERROR|Parse Error|Invalid call|Invalid access", ln)
              and not any(x in ln for x in IGNORED_GODOT)]
    probs = [f"godot: {ln.strip()}" for ln in errors[:20]]
    if r.returncode != 0:
        probs.append(f"godot: smoke script exited {r.returncode}")
    summary = next((ln for ln in lines if ln.startswith("SMOKE")), "no SMOKE line")
    return probs, summary


def check(loc, build=True):
    t0 = time.time()
    game = ROOT / "game"
    proc = None
    if build:
        cmd = [str(BLENDER), "--background", "--python-exit-code", "1", "--python", str(SCENE / "check_scene.py"),
               "--", "--location", loc]
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if not (game / data_path(loc)).exists():
        print(f"no export of {loc} yet ({data_path(loc)}): data and game checks skipped")
        probs, summary, gprobs, gsum = [], "no export", [], ""
    else:
        probs, summary = validate_game(game, loc)
        print(f"data: {summary}; {len(probs)} problems")
        gprobs, gsum = godot_smoke(game, None if loc == DEFAULT else data_path(loc))
    if gsum:
        print(f"godot: {gsum}; {len(gprobs)} problems")
    probs += gprobs
    if proc:
        output = proc.communicate()[0]
        lines = [ln for ln in output.splitlines() if ln.startswith(("CHECK", "Traceback", "Error"))
                 or ln.startswith("  File") or re.match(r"^\w+Error", ln)]
        print("\n".join(ln for ln in lines if ln.startswith("CHECK") and not ln.startswith("CHECK problem")))
        if proc.returncode != 0:
            probs += [f"scene: {ln}" for ln in lines if not ln.startswith("CHECK ok") and not ln.startswith("CHECK scene")]
            probs.append(f"scene: check_scene.py exited {proc.returncode}")
    dt = time.time() - t0
    for p in probs:
        print("  PROBLEM", p)
    print(f"check {'FAILED' if probs else 'passed'} in {dt:.0f}s")
    gpu._log({"name": f"{loc}/check", "start": gpu._stamp(t0), "end": gpu._stamp(time.time()), "seconds": round(dt, 1),
              "exit": 1 if probs else 0, "estimate_s": "", "cwd": str(ROOT), "cmd": "game.py check"})
    return 1 if probs else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--location", default=os.environ.get("GAME_LOCATION", "courtyard"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="build without rendering, validate the game data, run the game headless (the courtyard run plays the quest through all locations)")
    c.add_argument("--no-build", action="store_true", help="skip the Blender scene build (seconds instead of a minute)")
    p = sub.add_parser("preview", help="EEVEE still of the location")
    p.add_argument("--view", default="ref", help="ref, or a name of location.json views (eye, plan, ...)")
    p.add_argument("--percent", type=int, default=50)
    p.add_argument("--check-scale", action="store_true")
    p.add_argument("--force", action="store_true")
    for tier in TIERS:
        t = sub.add_parser(tier, help=f"{tier} game export: only stale steps run")
        t.add_argument("steps", nargs="*", help=f"some of {ORDER} (default: all)")
        t.add_argument("--force", action="store_true", help="run the steps even when they are up to date")
        if tier == "draft":
            t.add_argument("--full-frame", action="store_true", help="render the whole frame at the draft's samples")
            t.add_argument("--all-tiles", action="store_true",
                           help="the tiles step renders the tile of every hotspot (default: the first only)")
            t.add_argument("--to-game", action="store_true",
                           help="write into the location's game folder (not for the first location)")
    sub.add_parser("adopt", help="take the existing game/ export as up to date")
    st = sub.add_parser("status", help="which steps are stale")
    st.add_argument("--tier", choices=TIERS, default=None)
    args = ap.parse_args()
    loc = args.location
    if not (ROOT / "locations" / loc / "plan.json").exists():
        sys.exit(f"no location {loc} (locations/{loc}/plan.json)")
    if args.cmd == "check":
        sys.exit(check(loc, build=not args.no_build))
    if args.cmd == "preview":
        preview(loc, args.view, args.percent, args.check_scale, args.force)
    elif args.cmd in TIERS:
        global FULL_FRAME, ALL_TILES
        FULL_FRAME = getattr(args, "full_frame", False)
        ALL_TILES = getattr(args, "all_tiles", False)
        to_game = getattr(args, "to_game", False)
        if to_game and loc == DEFAULT:
            sys.exit("--to-game would overwrite the first location's export in game/; use it for another location")
        run_steps(args.cmd, args.steps, loc, args.force, to_game)
    elif args.cmd == "adopt":
        adopt(loc)
    elif args.cmd == "status":
        for tier in ([args.tier] if args.tier else TIERS):
            status(tier, loc)

if __name__ == "__main__":
    main()
