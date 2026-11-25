#!/usr/bin/env python3
"""One command from a character recipe to the game files of a speaking person.

    python3 scripts/character.py <id> [voice] [pick] [clips] [game]     # default: all four, in order
    python3 scripts/gpu.py run --name voice/<id> -- python3 scripts/character.py <id> voice

The recipe is characters/<id>/character.json:

    {"name": "Hedda", "voice": "hedda",          # a tools/say character (galley-v2 say-voices.json)
     "lines": ["lines.txt"],                     # say batch files; rows are line_01, line_02, ... in order
     "portrait": "final/portrait_768.jpg",       # the image InfiniteTalk animates
     "clip_prompt": "...", "idle_prompt": "...", # InfiniteTalk prompts for lines and the listening loop
     "face_crop": "crop=380:380:122:30",         # ffmpeg crop of the 624 px clip onto the face
     "distance": 2.5}                            # voice_room.py distance in metres

Steps (each skips work whose output exists; --force redoes it):

- voice: renders every line with tools/say, 3 takes, two lines per model load (a longer batch
  overflows Drama 3's context), into characters/<id>/voice/.
- pick: copies the passing take with the highest speaker similarity per line to
  final/line_NN.wav. Replace a pick by hand after listening; pick never overwrites one.
- clips: InfiniteTalk on RunPod for every final line, plus idle.mp4 from 8 s of silence and a
  seamless idle_loop.mp4 (the last second cross-faded into the start). $0.25 per clip.
- game: game/assets/npcs/<id>/: portrait.jpg, line_NN.wav through voice_room.py, and 320 px
  JPG frames per clip (line_NN/, idle/), cropped to the face.

Writing the person's game/data/npcs/<id>.json and dialogue stays by hand.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAY = Path.home() / "workspace/projects/galley-v2/tools/say"
BLENDER_PY = next(Path("/Applications/Blender.app/Contents/Resources").glob("*/python/bin/python3*"), None)
STEPS = ("voice", "pick", "clips", "game")
FPS = 25


def run(cmd: list, **kw) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def line_rows(src: Path, recipe: dict) -> list[str]:
    rows = []
    for name in recipe["lines"]:
        for row in (src / name).read_text().splitlines():
            if row.strip() and not row.startswith("#"):
                rows.append(row)
    return rows


def spoken(row: str) -> str:
    return row.split(":", 1)[1].strip() if ":" in row.split("[")[0] else row.strip()


def step_voice(cid: str, src: Path, recipe: dict, force: bool) -> None:
    rows = line_rows(src, recipe)
    out = src / "voice"

    def done(row: str) -> bool:
        return out.exists() and any(json.loads(p.read_text()).get("text") == spoken(row)
                                    for p in out.rglob("*.json") if not p.name.startswith("_"))

    def render(part: list[str], name: str, tmp: str) -> None:
        batch = Path(tmp) / f"{name}.txt"
        batch.write_text("\n".join(r if ":" in r.split("[")[0] else f"{recipe['voice']}: {r}" for r in part) + "\n")
        subprocess.run([str(SAY), "--batch", str(batch), "--takes", "3", "--out", str(out / name)])

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(0, len(rows), 2):
            part = [r for r in rows[i:i + 2] if force or not done(r)]
            if part:
                render(part, f"part_{i:02d}", tmp)
            # A long line next to a long reference can overflow the context; retry alone.
            for j, r in enumerate(part):
                if not done(r):
                    render([r], f"line_{i + j + 1:02d}", tmp)


def step_pick(cid: str, src: Path, recipe: dict, force: bool) -> None:
    takes = [json.loads(p.read_text()) | {"file": str(p.with_suffix(".wav"))}
             for p in (src / "voice").rglob("*.json") if not p.name.startswith("_")]
    final = src / "final"
    final.mkdir(exist_ok=True)
    for k, row in enumerate(line_rows(src, recipe), 1):
        dst = final / f"line_{k:02d}.wav"
        if dst.exists():
            continue
        mine = [t for t in takes if t.get("text") == spoken(row)]
        cands = [t for t in mine if t.get("pass")]
        # A take that fails only on long pauses is usable with its pauses shortened to 0.7 s.
        paused = [t for t in mine if t["reasons"] and all(r.startswith("silence") for r in t["reasons"])]
        if not cands and not paused:
            print(f"line_{k:02d}: no usable take; reword the line or render more takes", file=sys.stderr)
            continue
        best = max(cands or paused, key=lambda t: t.get("speaker_similarity") or 0)
        if cands:
            shutil.copy(best["file"], dst)
        else:
            run(["ffmpeg", "-loglevel", "error", "-i", best["file"], "-af",
                 "silenceremove=stop_periods=-1:stop_duration=1.0:stop_threshold=-45dB:stop_silence=0.7", dst])
        print(f"line_{k:02d}: take {best['take']}{'' if cands else ' (pauses shortened)'}, "
              f"similarity {best.get('speaker_similarity')}, {best['duration_s']} s")


def make_loop(src: Path, dst: Path) -> None:
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", str(src)]))
    t = dur - 1.0
    graph = (f"[0:v]split=3[a][b][c];[a]trim={t}:{dur},setpts=PTS-STARTPTS[tail];"
             f"[b]trim=0:1,setpts=PTS-STARTPTS[head];[c]trim=1:{t},setpts=PTS-STARTPTS[body];"
             f"[tail][head]xfade=transition=fade:duration=1:offset=0[blend];[blend][body]concat=n=2:v=1:a=0[v]")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex", graph, "-map", "[v]", "-an", dst])


def step_clips(cid: str, src: Path, recipe: dict, force: bool) -> None:
    final, clips = src / "final", src / "final" / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    portrait = src / recipe["portrait"]
    jobs = []
    for wav in sorted(final.glob("line_*.wav")):
        out = clips / f"{wav.stem}.mp4"
        if force or not out.exists():
            jobs.append((wav, out, recipe["clip_prompt"]))
    silence = final / "idle_silence.wav"
    if not silence.exists():
        run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", 8, silence])
    if force or not (clips / "idle.mp4").exists():
        jobs.append((silence, clips / "idle.mp4", recipe["idle_prompt"]))

    def one(job):
        wav, out, prompt = job
        run([sys.executable, ROOT / "scripts/infinitetalk.py", portrait, wav, out, "--prompt", prompt])

    with ThreadPoolExecutor(3) as pool:   # remote jobs; three at a time keeps the endpoint queue short
        list(pool.map(one, jobs))
    if (clips / "idle.mp4").exists() and (force or not (clips / "idle_loop.mp4").exists()):
        make_loop(clips / "idle.mp4", clips / "idle_loop.mp4")


def frames(clip: Path, dst: Path, crop: str) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    run(["ffmpeg", "-loglevel", "error", "-i", clip, "-vf", f"{crop},scale=320:320,fps={FPS}", "-q:v", 3,
         dst / "%04d.jpg"])


def step_game(cid: str, src: Path, recipe: dict, force: bool) -> None:
    out = ROOT / "game/assets/npcs" / cid
    out.mkdir(parents=True, exist_ok=True)
    crop = recipe["face_crop"]
    clips = src / "final" / "clips"
    first = next(iter(sorted(clips.glob("*.mp4"))), None)
    if first:
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", first, "-vf", f"{crop},scale=320:320", "-frames:v", 1,
             "-q:v", 2, out / "portrait.jpg"])
    for wav in sorted((src / "final").glob("line_*.wav")):
        dst = out / wav.name
        if force or not dst.exists():
            run([BLENDER_PY, ROOT / "scripts/voice_room.py", wav, dst, "--distance", recipe.get("distance", 2.5)])
    for clip in sorted(clips.glob("line_*.mp4")):
        if force or not (out / clip.stem).exists():
            frames(clip, out / clip.stem, crop)
    loop = clips / "idle_loop.mp4"
    if loop.exists() and (force or not (out / "idle").exists()):
        frames(loop, out / "idle", crop)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("steps", nargs="*", help=f"some of {', '.join(STEPS)} (default: all)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if bad := set(a.steps) - set(STEPS):
        ap.error(f"unknown steps {sorted(bad)}")
    src = ROOT / "characters" / a.id
    recipe = json.loads((src / "character.json").read_text())
    for step in [s for s in STEPS if s in (a.steps or STEPS)]:
        print(f"== {a.id} {step}", flush=True)
        globals()[f"step_{step}"](a.id, src, recipe, a.force)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
