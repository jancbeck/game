#!/usr/bin/env python3
"""Release data and the macOS app.

    scripts/release.py build   [--format astc|bc6h|astc8] [--jobs N] [--force]
    scripts/release.py templates                  # install the Godot export templates for this version
    scripts/release.py export  [--no-build] [--out dist/Courtyard.app]
    scripts/release.py compare [--tiles forge,well,gate]
    scripts/release.py measure [--app dist/Courtyard.app]
    scripts/release.py run     [--app dist/Courtyard.app]
    scripts/release.py check   [--app dist/Courtyard.app]

build     Converts the exports of every location (the courtyard in game/assets/, each other in
          game/locations/<name>/assets/) to GPU-compressed release data in game/release/
          (game/scripts/release_build.gd): every EXR layer as a .gtx (ASTC 4x4 HDR by default,
          BC6H with --format bc6h), every depth.f32 as a lossless PNG, and release/game_data.pck
          with those and every other runtime file (characters, people's clips, skill and ambient
          audio, the LUT). The exports are not touched. Incremental: files whose source did not
          change are skipped, so a location that is re-rendered costs only its own layers on the
          next build. No GPU needed.
templates Downloads Godot_v<version>_export_templates.tpz from the godotengine GitHub release of
          the installed version, checks its SHA-512 against the release's SHA512-SUMS.txt and
          unpacks it to ~/Library/Application Support/Godot/export_templates/<version>/.
export    Builds the data if needed, exports the project with the "macOS" preset of
          game/export_presets.cfg into dist/Courtyard.app (the official templates are universal;
          the executable is thinned to arm64), puts game_data.pck into the bundle and signs
          it ad hoc. The scene.json and hotspots.json of every location travel in the main pack
          (include_filter `locations/*/data/*`).
compare   Runs the game twice through the GPU queue, on the raw EXRs and on the release data,
          saves frames of the background alone into renders/release/{raw,release}/ and prints the
          difference (needs numpy and Pillow: run it with .venv/bin/python).
measure   Startup, video memory, frame times, and disk size, raw against release, as queue jobs.
run       Starts the exported app through the queue with the perf check and reports its startup.
check     Starts the exported app through the queue with --release-check: the title, New game, then a
          visit to every location (the courtyard and each locations/<name>/), which must all load from
          the data pack. Prints how long each takes to appear; screenshots go to renders/release/app/.

The game reads the release data on its own when it is current (scene_data.gd); `--raw` after `--`
on the Godot command line reads the raw files instead.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gpu  # noqa: E402

GODOT = Path(os.environ.get("GODOT", "/Applications/Godot.app/Contents/MacOS/Godot"))
GAME = ROOT / "game"
RELEASE = GAME / "release"
DIST = ROOT / "dist"
APP_NAME = "Courtyard"
PRESET = "macOS"
DATA_PACK = "game_data.pck"
TEMPLATES = Path.home() / "Library/Application Support/Godot/export_templates"


# ---------- helpers ----------

def godot_version():
    """'4.7.2.stable' from `Godot --version` ('4.7.2.stable.official.ed1daf0bf')."""
    out = subprocess.run([GODOT, "--version"], capture_output=True, text=True).stdout.strip()
    m = re.match(r"(\d+\.\d+(?:\.\d+)?\.[a-z0-9]+)", out)
    if not m:
        sys.exit(f"cannot read the Godot version from {out!r}")
    return m.group(1)


def godot(*args, check=True, log=None):
    cmd = [str(GODOT), "--headless", "--path", str(GAME), *args]
    print("+", " ".join(cmd[1:]), flush=True)
    if log:
        with open(log, "w") as f:
            p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    else:
        p = subprocess.run(cmd)
    if check and p.returncode != 0:
        sys.exit(f"Godot exited with {p.returncode}")
    return p.returncode


def mb(n):
    return f"{n / 1048576:.0f} MB"


def tree_size(path):
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


# ---------- build ----------

def build(args):
    a = ["--script", "res://scripts/release_build.gd", "--", f"--format={args.format}"]
    if args.jobs:
        a.append(f"--jobs={args.jobs}")
    if args.force:
        a.append("--force")
    godot(*a)
    print(f"release data: {mb(tree_size(RELEASE))} in {RELEASE}")


# ---------- templates and export ----------

def templates(args):
    version = godot_version()
    target = TEMPLATES / version
    if (target / "macos.zip").exists():
        print(f"export templates {version} are installed: {target}")
        return
    base = f"https://github.com/godotengine/godot/releases/download/{version.replace('.stable', '')}-stable"
    name = f"Godot_v{version.replace('.stable', '')}-stable_export_templates.tpz"
    tmp = ROOT / "renders" / "release" / "templates"
    tmp.mkdir(parents=True, exist_ok=True)
    tpz = tmp / name
    print(f"downloading {base}/{name}")
    urllib.request.urlretrieve(f"{base}/{name}", tpz)
    sums = urllib.request.urlopen(f"{base}/SHA512-SUMS.txt").read().decode()
    want = next(line.split()[0] for line in sums.splitlines() if line.endswith(name))
    h = hashlib.sha512()
    with open(tpz, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != want:
        sys.exit(f"SHA-512 of {name} does not match the release's SHA512-SUMS.txt")
    print("SHA-512 matches")
    unpack = tmp / "unpacked"
    shutil.rmtree(unpack, ignore_errors=True)
    subprocess.run(["unzip", "-q", str(tpz), "-d", str(unpack)], check=True)
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    shutil.move(str(unpack / "templates"), str(target))
    print(f"installed {target}")


def export(args):
    version = godot_version()
    if not (TEMPLATES / version / "macos.zip").exists():
        sys.exit(f"no export templates for {version}: run scripts/release.py templates")
    if not (GAME / "export_presets.cfg").exists():
        sys.exit("game/export_presets.cfg is missing")
    if not args.no_build:
        build(argparse.Namespace(format="astc", jobs=0, force=False))
    if not (RELEASE / DATA_PACK).exists():
        sys.exit(f"{RELEASE / DATA_PACK} is missing: run scripts/release.py build")
    out = (ROOT / args.out).resolve()
    shutil.rmtree(out, ignore_errors=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    godot("--import", check=False)           # a fresh checkout has no .godot/ yet
    godot("--export-release", PRESET, str(out))
    if not out.exists():
        sys.exit("the export produced no app")
    shutil.copy2(RELEASE / DATA_PACK, out / "Contents/Resources" / DATA_PACK)
    # the official templates are universal; the release data (ASTC HDR) needs an Apple GPU, so keep arm64
    exe = out / "Contents/MacOS" / APP_NAME
    thin = exe.with_suffix(".arm64")
    subprocess.run(["lipo", "-thin", "arm64", str(exe), "-output", str(thin)], check=True)
    thin.replace(exe)
    subprocess.run(["codesign", "--force", "--deep", "-s", "-", str(out)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(out)], check=True)
    print(f"app: {out}  {mb(tree_size(out))}")
    for p in sorted((out / "Contents/Resources").iterdir()):
        print(f"  {p.name:<28} {mb(tree_size(p))}")


# ---------- running the game ----------

def game_cmd(extra, app=None, res=None):
    """The command of one windowed game run (the project's own window size unless `res` is given);
    arguments for the game itself follow `--`."""
    size = ["--resolution", res] if res else []
    if app:
        return [str(Path(app) / "Contents/MacOS" / APP_NAME), *size, "--audio-driver", "Dummy", "--", *extra]
    return [str(GODOT), "--path", str(GAME), *size, "--audio-driver", "Dummy", "--", *extra]


def run_job(name, cmd, log):
    """One queue job with /usr/bin/time -l; returns (exit code, peak memory footprint in bytes)."""
    code = gpu.run(name, ["/usr/bin/time", "-l", *cmd], cwd=ROOT, log=log)
    text = Path(log).read_text(errors="replace")
    m = re.search(r"(\d+)\s+peak memory footprint", text)
    return code, int(m.group(1)) if m else None


def parse_log(text):
    """Numbers from the game's output."""
    r = {}
    m = re.search(r"startup: loaded at (\d+) ms, first frame at (\d+) ms, video memory (\d+) MB", text)
    if m:
        r["loaded_ms"], r["first_frame_ms"], r["vram_start_mb"] = map(int, m.groups())
    m = re.search(r"layers: base \+ (\d+) groups.* loaded in (\d+) ms", text)
    if m:
        r["layers_ms"] = int(m.group(2))
    r["tiles"] = [(m.group(1), int(m.group(2)), float(m.group(3))) for m in
                  re.finditer(r"tile (\w+): \d+ groups, decoded in (\d+) ms on a worker, uploaded over \d+ frames \(([\d.]+) ms", text)]
    r["frames"] = {m.group(1): (float(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5)))
                   for m in re.finditer(r"frame ([\w ]+): ([\d.]+) ms per frame, world GPU ([\d.]+) ms, video memory (\d+) MB, texture memory (\d+) MB", text)}
    return r


def perf_rows(csv_path, start_line):
    """Rows of logs/perf.csv written since the run began."""
    rows = []
    for line in csv_path.read_text().splitlines()[start_line:]:
        p = line.split(",")
        if len(p) >= 9:
            rows.append(p)
    return rows


def perf_summary(rows):
    win = [r for r in rows if r[1] == "window" and r[2]]
    # the first windows belong to loading; steady state is the rest
    if not win:
        return {}
    steady = win[1:] if len(win) > 1 else win
    return {"mean_ms": statistics.mean(float(r[2]) for r in steady),
            "p99_ms": max(float(r[3]) for r in steady),
            "worst_ms": max(float(r[4]) for r in win),
            "vram_mb": max(float(r[7]) for r in win),
            "hitches": sum(1 for r in rows if r[1] == "hitch")}


def measure(args):
    out_dir = ROOT / "renders" / "release" / "measure"
    out_dir.mkdir(parents=True, exist_ok=True)
    perf_csv = GAME / "logs" / "perf.csv"
    if args.app:
        perf_csv = Path.home() / "Library/Application Support/Godot/app_userdata" / APP_NAME / "logs/perf.csv"
    results = {}
    modes = [("raw", ["--raw"]), ("release", [])]
    if args.app:
        modes = [("app", [])]
    for mode, flags in modes:
        res = {}
        # 1. the whole game: startup, and the perf check (idle, four tile loads and zooms)
        before = len(perf_csv.read_text().splitlines()) if perf_csv.exists() else 0
        log = out_dir / f"{mode}_perf.log"
        code, peak = run_job(f"courtyard/release/measure-{mode}-perf",
                             game_cmd(["--no-intro", "--perf-check", *flags], args.app), log)
        res.update(parse_log(log.read_text(errors="replace")))
        res["peak_footprint"] = peak
        if perf_csv.exists():
            res["perf"] = perf_summary(perf_rows(perf_csv, before))
        # 2. the background alone, frozen: frame times and memory of each view
        shots = out_dir / mode
        log = out_dir / f"{mode}_shot.log"
        code, peak = run_job(f"courtyard/release/measure-{mode}-shot",
                             game_cmd([f"--release-shot={shots}", *flags], args.app), log)
        res["shot"] = parse_log(log.read_text(errors="replace"))
        results[mode] = res
    (out_dir / ("results_app.json" if args.app else "results.json")).write_text(json.dumps(results, indent=1))
    print_measure(results)


def disk_sizes():
    """Bytes of the files the game reads for HDR layers and depth, raw and release."""
    raw = sum(p.stat().st_size for p in (GAME / "assets").rglob("*") if p.suffix in (".exr", ".f32") and p.is_file())
    rel = sum(p.stat().st_size for p in RELEASE.rglob("*") if p.suffix in (".gtx", ".png") and p.is_file()) if RELEASE.exists() else 0
    return raw, rel


def print_measure(results):
    raw, rel = disk_sizes()
    print()
    print(f"disk, HDR layers + depth: raw {mb(raw)}, release {mb(rel)}")
    for mode, r in results.items():
        print(f"\n{mode}")
        print(f"  loaded at {r.get('loaded_ms')} ms, first frame at {r.get('first_frame_ms')} ms (since engine start); "
              f"layers {r.get('layers_ms')} ms; video memory at first frame {r.get('vram_start_mb')} MB; "
              f"peak footprint {mb(r['peak_footprint']) if r.get('peak_footprint') else '?'}")
        for tid, dec, up in r.get("tiles", []):
            print(f"  tile {tid}: decoded {dec} ms on a worker, {up:.1f} ms on the main thread")
        p = r.get("perf")
        if p:
            print(f"  perf check (vsync): mean {p['mean_ms']:.2f} ms, worst p99 {p['p99_ms']:.1f} ms, worst frame {p['worst_ms']:.0f} ms, "
                  f"hitches {p['hitches']}, video memory up to {p['vram_mb']:.0f} MB")
        for view, (wall, gpu_ms, vram, tex) in r.get("shot", {}).get("frames", {}).items():
            print(f"  {view:<12} {wall:.2f} ms/frame (vsync off), GPU {gpu_ms:.2f} ms, video {vram} MB, textures {tex} MB")


def run_app(args):
    app = Path(args.app)
    log = ROOT / "renders" / "release" / "app.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    code, peak = run_job("courtyard/release/app", game_cmd(["--no-intro", "--perf-check"], app), log)
    r = parse_log(log.read_text(errors="replace"))
    print(f"exit {code}; loaded at {r.get('loaded_ms')} ms, first frame at {r.get('first_frame_ms')} ms, "
          f"video memory {r.get('vram_start_mb')} MB, peak footprint {mb(peak) if peak else '?'}")
    sys.exit(code)


def check_app(args):
    """The app (or the project, with --app "") through the title, a new game and every location."""
    app = Path(args.app) if args.app else None
    out = ROOT / "renders" / "release" / "app"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    log = ROOT / "renders" / "release" / "app_check.log"
    code, peak = run_job("release/app-check", game_cmd(["--release-check", f"--shots-dir={out}"], app), log)
    text = log.read_text(errors="replace")
    keep = ("PLAYTHROUGH", "data pack:", "hdr:", "startup:", "data: ")
    for line in text.splitlines():
        if line.startswith(keep) and not line.startswith("PLAYTHROUGH shot"):
            print(line)
    print(f"exit {code}; peak memory footprint {mb(peak) if peak else '?'}; log {log}; screenshots {out}")
    sys.exit(code)


# ---------- compare ----------

def compare(args):
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit("compare needs numpy and Pillow: run it as .venv/bin/python scripts/release.py compare")
    base = ROOT / "renders" / "release"
    tiles = args.tiles
    for mode, flags in (("raw", ["--raw"]), ("release", [])):
        out = base / mode
        shutil.rmtree(out, ignore_errors=True)
        log = base / f"{mode}_shot.log"
        code, _ = run_job(f"courtyard/release/shot-{mode}",
                          game_cmd([f"--release-shot={out}", f"--tiles={tiles}", *flags], res="2560x1440"), log)
        if code != 0:
            sys.exit(f"the {mode} run failed, see {log}")
    names = ["wide", "main"] + [f"tile_{t}" for t in tiles.split(",")]
    print(f"\n{'view':<14}{'max':>5}{'mean':>8}{'p99.9':>7}{'>=2':>9}{'>=4':>9}   dark (<10% of range): mean  max   >=2")
    for n in names:
        a = np.asarray(Image.open(base / "raw" / f"{n}.png").convert("RGB"), dtype=np.int16)
        b = np.asarray(Image.open(base / "release" / f"{n}.png").convert("RGB"), dtype=np.int16)
        d = np.abs(a - b)
        dm = d.max(axis=2)
        lum = a.mean(axis=2)
        dark = lum < 25.5
        print(f"{n:<14}{dm.max():>5}{d.mean():>8.3f}{np.percentile(dm, 99.9):>7.0f}"
              f"{(dm >= 2).mean() * 100:>8.2f}%{(dm >= 4).mean() * 100:>8.2f}%"
              f"   {d[dark].mean() if dark.any() else 0:.3f}  {dm[dark].max() if dark.any() else 0:>3}  "
              f"{(dm[dark] >= 2).mean() * 100 if dark.any() else 0:.2f}%  ({dark.mean() * 100:.0f}% of the view is dark)")
        # amplified difference and side-by-side crop of the darkest busy region, for looking at it
        amp = np.clip(dm * 32, 0, 255).astype(np.uint8)
        Image.fromarray(amp).save(base / f"diff_x32_{n}.png")
    print(f"\ndifference images (x32) and both runs' frames: {base}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--format", default="astc", choices=["astc", "bc6h", "astc8"])
    b.add_argument("--jobs", type=int, default=0)
    b.add_argument("--force", action="store_true")
    sub.add_parser("templates")
    e = sub.add_parser("export")
    e.add_argument("--no-build", action="store_true")
    e.add_argument("--out", default=f"dist/{APP_NAME}.app")
    c = sub.add_parser("compare")
    c.add_argument("--tiles", default="forge,well,gate")
    m = sub.add_parser("measure")
    m.add_argument("--app")
    r = sub.add_parser("run")
    r.add_argument("--app", default=f"dist/{APP_NAME}.app")
    k = sub.add_parser("check")
    k.add_argument("--app", default=f"dist/{APP_NAME}.app")
    args = ap.parse_args()
    {"build": build, "templates": templates, "export": export, "compare": compare,
     "measure": measure, "run": run_app, "check": check_app}[args.cmd](args)


if __name__ == "__main__":
    main()
