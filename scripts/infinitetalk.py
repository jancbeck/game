"""Animate a portrait to a voice line with InfiniteTalk on RunPod's public endpoint.

    python3 scripts/infinitetalk.py IMAGE AUDIO OUT.mp4 [--size 480p|720p] [--prompt TEXT]

IMAGE and AUDIO are local files or http(s) URLs. Local files are sent inline as data URLs.
RUNPOD_API_KEY must be set. The job runs on RunPod's hosted endpoint (pay per video, about
$0.25 at 480p and $0.50 at 720p); no pod is started. The script submits with runsync, polls
the status until the job ends, and downloads the video, whose URL expires after 7 days.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.runpod.ai/v2/infinitetalk"


def as_url(src):
    if src.startswith(("http://", "https://", "data:")):
        return src
    mime = mimetypes.guess_type(src)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(Path(src).read_bytes()).decode()


def call(url, payload=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={"Authorization": f"Bearer {os.environ['RUNPOD_API_KEY']}",
                                          "Content-Type": "application/json"},
                                 method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"status": "FAILED", "error": f"HTTP {e.code}: {e.read().decode()[:500]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--size", default="480p", choices=("480p", "720p"))
    ap.add_argument("--prompt", default="a person speaking calmly, natural subtle head movement")
    args = ap.parse_args()

    t0 = time.time()
    job = call(f"{API}/runsync", {"input": {"prompt": args.prompt, "image": as_url(args.image),
                                            "audio": as_url(args.audio), "size": args.size,
                                            "enable_safety_checker": True}})
    while job.get("status") in ("IN_QUEUE", "IN_PROGRESS"):
        time.sleep(5)
        job = call(f"{API}/status/{job['id']}")
    if job.get("status") != "COMPLETED":
        sys.exit(f"InfiniteTalk failed: {job.get('status')} {job.get('error')}")
    out = job["output"]
    video = out.get("result") or out.get("video_url")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(video, args.out)
    print(f"{args.out}: {time.time() - t0:.0f} s, cost {out.get('cost')} USD, "
          f"queue {job.get('delayTime')} ms, run {job.get('executionTime')} ms")


if __name__ == "__main__":
    main()
