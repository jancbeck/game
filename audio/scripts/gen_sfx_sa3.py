#!/usr/bin/env python3
"""Render the SFX list with Stable Audio 3 through the galley-v2 tools/sfx wrapper.

Usage: gen_sfx_sa3.py [--list sfx|game_sfx] [--out DIR] [--takes K] [--seed 1000]
                      [--only id,id] [--cfg-override id=2.0,...]

--list picks the list in prompts.json (default sfx). An item's own "takes" wins over
--takes when --takes is not given. --out defaults to sfx/stable-audio-3 (sfx/game for
game_sfx).

Each call runs under /usr/bin/time -l to record peak memory. Results are appended
to audio/sfx/stable-audio-3/_run_log.jsonl. Must run outside the sandbox (Metal).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

AUDIO = Path(__file__).resolve().parent.parent
SFX_TOOL = "/Users/jan/workspace/projects/galley-v2/tools/sfx"
OUT = AUDIO / "sfx" / "stable-audio-3"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="sfx")
    ap.add_argument("--out", default="")
    ap.add_argument("--takes", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--only", default="")
    ap.add_argument("--cfg-override", default="", help="id=cfg,id=cfg")
    args = ap.parse_args()

    items = json.loads((AUDIO / "prompts.json").read_text())[args.list]
    out = Path(args.out) if args.out else (OUT if args.list == "sfx" else AUDIO / "sfx" / "game")
    only = {s for s in args.only.split(",") if s}
    cfg_over = dict(kv.split("=") for kv in args.cfg_override.split(",") if kv)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "_run_log.jsonl"

    for it in items:
        if only and it["id"] not in only:
            continue
        sa3 = it["sa3"]
        cfg = float(cfg_over.get(it["id"], sa3["cfg"]))
        takes = args.takes or it.get("takes", 2)
        cmd = ["/usr/bin/time", "-l", SFX_TOOL, sa3["prompt"], "--seconds", str(it["seconds"]),
               "--takes", str(takes), "--seed", str(args.seed), "--neg", sa3["neg"],
               "--cfg", str(cfg), "--out", str(out), "--name", it["id"]]
        t0 = time.monotonic()
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        wall = round(time.monotonic() - t0, 1)
        rss = re.search(r"(\d+)\s+maximum resident set size", proc.stderr)
        foot = re.search(r"(\d+)\s+peak memory footprint", proc.stderr)
        rec = {"id": it["id"], "cfg": cfg, "takes": takes, "seed": args.seed,
               "wall_total_s": wall, "returncode": proc.returncode,
               "max_rss_gb": round(int(rss.group(1)) / 2**30, 2) if rss else None,
               "peak_footprint_gb": round(int(foot.group(1)) / 2**30, 2) if foot else None}
        with log.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout[-1500:] + proc.stderr[-1500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
