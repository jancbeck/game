#!/usr/bin/env python3
"""Make loop versions of the beds and normalize every file to -16 LUFS.

Run with the Stable Audio 3 venv python (numpy + soundfile) and ffmpeg on PATH:
  <sa3-venv>/bin/python audio/scripts/postprocess.py [DIR ...]

For each DIR (default: every model folder under audio/sfx):
  1. beds flagged "loop" in prompts.json get <id>_t<k>_loop.wav: the tail is
     cross-faded (equal power) into the head, so the file repeats without a seam;
  2. every WAV is normalized into DIR/norm/ with ffmpeg loudnorm (two pass, linear,
     I=-16, TP=-1.0). When loudnorm cannot reach the target, a gain plus a 4x
     oversampled peak limiter is used instead. Sound effects also get a 30 Hz
     high-pass first;
  3. DIR/norm/_levels.csv records the level before and after.
The original files are never changed.
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AUDIO = Path(__file__).resolve().parent.parent
TARGET = -16.0
TP = -1.0


def ebur128(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = out[out.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", s).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s).group(1))
    return lufs, peak


def make_loop(src: Path, dst: Path, fade_s: float):
    x, sr = sf.read(src, dtype="float32")
    n = len(x)
    f = min(int(fade_s * sr), n // 3)
    t = np.linspace(0, np.pi / 2, f, dtype=np.float32)
    fin, fout = np.sin(t), np.cos(t)
    if x.ndim > 1:
        fin, fout = fin[:, None], fout[:, None]
    head = x[:f] * fin + x[n - f:] * fout
    y = np.concatenate([head, x[f:n - f]], axis=0)
    sf.write(dst, y, sr, subtype="PCM_16")


def loudnorm(src: Path, dst: Path, pre: str = ""):
    sr = sf.info(src).samplerate
    base = f"{pre}loudnorm=I={TARGET}:TP={TP}:LRA=20"
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                         base + ":print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    m = json.loads(p1[p1.rfind("{"):p1.rfind("}") + 1])
    flt = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
           f"offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                    "-af", flt, "-ar", str(sr), "-c:a", "pcm_s16le", str(dst)], check=True)
    lufs, peak = ebur128(dst)
    method = "loudnorm"
    if abs(lufs - TARGET) > 0.7:
        # peaky material: raise the gain, limit at 4x oversampling (true peak), and
        # correct the gain until the measured loudness is within 0.3 LU of the target
        gain = TARGET - ebur128(src)[0]
        for _ in range(5):
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                            "-af", f"{pre}volume={gain}dB,aresample={sr * 4},"
                                   f"alimiter=limit=0.89:attack=1:release=40:level=false,"
                                   f"aresample={sr}",
                            "-c:a", "pcm_s16le", str(dst)], check=True)
            lufs, peak = ebur128(dst)
            if abs(lufs - TARGET) <= 0.3:
                break
            gain += TARGET - lufs
        method = "gain+limiter"
    return lufs, peak, method


def main(dirs):
    loops = {it["id"]: it for it in json.loads((AUDIO / "prompts.json").read_text())["sfx"]
             if it.get("loop")}
    for d in dirs:
        d = Path(d)
        if d.parent.name == "sfx":
            for wav in sorted(d.glob("*_t[0-9].wav")):
                item = wav.name.rsplit("_t", 1)[0]
                if item in loops:
                    fade = 2.0 if loops[item]["seconds"] >= 15 else 1.5
                    make_loop(wav, wav.with_name(wav.stem + "_loop.wav"), fade)
        norm = d / "norm"
        norm.mkdir(exist_ok=True)
        # 2nd-order high-pass at 30 Hz removes sub-bass drift that eats limiter
        # headroom without being audible
        pre = "highpass=f=30," if d.parent.name == "sfx" else ""
        rows = []
        for wav in sorted(d.glob("*.wav")):
            before, bpeak = ebur128(wav)
            after, apeak, method = loudnorm(wav, norm / wav.name, pre)
            rows.append([wav.name, f"{before:.1f}", f"{bpeak:.1f}", f"{after:.1f}",
                         f"{apeak:.1f}", method])
            print(d.name, *rows[-1], flush=True)
        with (norm / "_levels.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["file", "lufs_before", "tp_before_dbfs", "lufs_after", "tp_after_dbfs",
                        "method"])
            w.writerows(rows)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = [str(p) for p in sorted(AUDIO.glob("sfx/*")) if p.is_dir()]
    main(args)
