#!/usr/bin/env python3
"""Render the SFX list with MOSS-SoundEffect v2.0 (MLX).

Run with audio/.venvs/moss/bin/python, outside the sandbox (Metal).
The weights directory comes from MOSS_SFX_MLX_WEIGHTS_DIR or --model-dir.

Usage: gen_sfx_moss.py [--steps 50] [--cfg 4.0] [--takes 1] [--seed 1000]
                       [--only id,id] [--out DIR] [--model-dir DIR]

The prompt and negative prompt are the same as for Stable Audio 3 (prompts.json).
Writes <id>_t<k>.wav (48 kHz mono 16-bit) and a .json sidecar per take.
"""
import argparse
import json
import resource
import time
import wave
from pathlib import Path

import numpy as np

AUDIO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = AUDIO / "sfx" / "moss"


def save_wav(path, audio, sr):
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[0])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.T.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--cfg", type=float, default=4.0)
    ap.add_argument("--takes", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--model-dir", default=None)
    ap.add_argument("--no-neg", action="store_true", help="empty negative prompt")
    args = ap.parse_args()

    import mlx.core as mx
    from moss_sfx_mlx.pipeline_mlx import MossSoundEffectPipeline

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = json.loads((AUDIO / "prompts.json").read_text())["sfx"]
    only = {s for s in args.only.split(",") if s}

    t0 = time.monotonic()
    pipe = MossSoundEffectPipeline.from_pretrained(args.model_dir)
    load_s = round(time.monotonic() - t0, 1)
    print(f"model load {load_s}s", flush=True)

    for it in items:
        if only and it["id"] not in only:
            continue
        prompt = it["sa3"]["prompt"]
        neg = "" if args.no_neg else it["sa3"]["neg"]
        for k in range(1, args.takes + 1):
            seed = args.seed + k - 1
            mx.reset_peak_memory()
            t1 = time.monotonic()
            audio = pipe(prompt=prompt, seconds=it["seconds"], num_inference_steps=args.steps,
                         cfg_scale=args.cfg, seed=seed, negative_prompt=neg,
                         progress_bar_cmd=lambda x, **kw: x)
            arr = np.array(audio[0]).astype(np.float32)
            wall = round(time.monotonic() - t1, 1)
            peak_float = float(np.abs(arr).max())
            wav = out / f"{it['id']}_t{k}.wav"
            save_wav(wav, arr, pipe.sample_rate)
            meta = {"prompt": prompt, "negative_prompt": neg or None, "seed": seed,
                    "seconds": it["seconds"], "steps": args.steps, "cfg": args.cfg,
                    "sigma_shift": 5.0, "model": "mlx-community/MOSS-SoundEffect-v2.0-bf16",
                    "sample_rate": pipe.sample_rate, "channels": 1,
                    "wall_seconds": wall, "model_load_seconds": load_s,
                    "mlx_peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2),
                    "float_peak_before_clip": round(peak_float, 3), "file": wav.name}
            wav.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
            print(f"{wav.name}  {wall}s  mlx_peak={meta['mlx_peak_memory_gb']}GB  "
                  f"float_peak={peak_float:.2f}", flush=True)

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**30
    print(f"process max RSS {rss:.2f} GB")


if __name__ == "__main__":
    main()
