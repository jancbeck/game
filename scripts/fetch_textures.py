#!/usr/bin/env python3
"""Download the scanned CC0 texture sets the materials use, from Poly Haven.

Usage (from the project root):

    python3 scripts/fetch_textures.py

Files land in scene/textures/<asset_id>/<map>.jpg, for example
scene/textures/rough_wood/diff.jpg. The folder is gitignored; run this once per
machine. Existing files with the expected size are skipped, so a rerun is cheap.

Sets (2k JPG, about 40 MB in total):

| Asset | Used by | Why |
|-------|---------|-----|
| rough_wood | wood_old, wood_dark, door_wood | Weathered, split timber with deep cracks along the grain; no plank seams, so it fits single boards and beams |
| rock_05 | stone_wall, cobble_wet | Pitted, rough rock face without block joints; a detail layer under the procedural block layout |
| rust_coarse_01 | iron | Coarse rust and pitting for hand-forged iron |

Only api.polyhaven.com and dl.polyhaven.org are contacted. Standard library only.
"""

import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "scene" / "textures"
API = "https://api.polyhaven.com/files/{}"
ALLOWED_HOSTS = {"api.polyhaven.com", "dl.polyhaven.org"}
RESOLUTION = "2k"
UA = {"User-Agent": "courtyard-scene-texture-fetch/1.0"}

# local file name -> Poly Haven map key
MAPS = {"diff": "Diffuse", "nor_gl": "nor_gl", "rough": "Rough", "disp": "Displacement"}
ASSETS = {
    "rough_wood": MAPS,
    "rock_05": MAPS,
    "rust_coarse_01": MAPS,
}


def _get(url):
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to download from {host}: {url}")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as e:
            if attempt == 5:
                raise
            print(f"retry {url}: {e!r}")
            time.sleep(1 + attempt)


def main():
    total = 0
    for asset, maps in ASSETS.items():
        files = json.loads(_get(API.format(asset)))
        folder = DEST / asset
        folder.mkdir(parents=True, exist_ok=True)
        for local, key in maps.items():
            entry = files[key][RESOLUTION]["jpg"]
            path = folder / f"{local}.jpg"
            if path.exists() and path.stat().st_size == entry["size"]:
                print(f"ok    {path.relative_to(ROOT)}")
            else:
                data = _get(entry["url"])
                if len(data) != entry["size"]:
                    sys.exit(f"size mismatch for {entry['url']}: {len(data)} != {entry['size']}")
                path.write_bytes(data)
                print(f"fetch {path.relative_to(ROOT)}  ({len(data) / 1e6:.1f} MB)")
            total += entry["size"]
    print(f"{total / 1e6:.0f} MB in {DEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
