#!/usr/bin/env python3
"""Download what the character build needs, into characters/vendor/ (gitignored).

Usage (from the project root):

    python3 scripts/fetch_character_assets.py            # everything
    python3 scripts/fetch_character_assets.py --no-system-assets   # skip the asset pack parts

The asset pack is read with HTTP range requests, so only the folders in SYSTEM_ASSET_PREFIXES are
downloaded, not the whole archive.

| What | From | Size | Licence |
|------|------|------|---------|
| MPFB 2.0.18 Blender extension | extensions.blender.org | 46 MB | GPL-3.0-or-later (code); base mesh, targets, rigs CC0 |
| Parts of makehuman_system_assets_cc0.zip | files2.makehumancommunity.org | 30 MB of 267 MB | CC0 (skins, eyes, eyebrows, eyelashes) |
| CMU Graphics Lab Motion Capture BVH (about twenty clips) | github.com/meshula/cmu-mocap | 8 MB | "free for use in research and commercial projects" |

The CMU clips are Bruce Hahne's MotionBuilder-friendly BVH conversion of the CMU database
(mocap.cs.cmu.edu). MPFB is installed into characters/vendor/blender/ext through Blender's own
extension installer, with BLENDER_USER_RESOURCES and BLENDER_USER_EXTENSIONS pointing there, so
the user's Blender folders are not touched. Existing files are skipped, so a rerun is cheap.

Only the hosts in ALLOWED_HOSTS are contacted. Standard library only.
"""

import argparse
import hashlib
import http.client
import io
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "characters" / "vendor"
DL = VENDOR / "dl"
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
ALLOWED_HOSTS = {
    "extensions.blender.org",
    "files2.makehumancommunity.org",
    "files.makehumancommunity.org",
    "raw.githubusercontent.com",
}
UA = {"User-Agent": "courtyard-character-fetch/1.0"}

MPFB_SHA = "c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad"
MPFB_URL = (
    f"https://extensions.blender.org/download/sha256:{MPFB_SHA}/add-on-mpfb-v2.0.18.zip"
    "?repository=%2Fapi%2Fv1%2Fextensions%2F&blender_version_min=4.2.0"
)
SYSTEM_ASSETS_URL = (
    "https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/"
    "makehuman_system_assets_cc0.zip"
)
SYSTEM_ASSET_PREFIXES = (
    "skins/young_caucasian_male/", "skins/middleage_caucasian_male/", "skins/old_caucasian_male/",
    "skins/old_caucasian_female/", "skins/middleage_caucasian_female/",
    "eyes/low-poly/", "eyes/materials/brown", "eyes/materials/blue.", "eyes/materials/blue_eye",
    "eyes/materials/grey", "eyebrows/eyebrow001/", "eyebrows/eyebrow004/", "eyelashes/eyelashes01/",
    "proxymeshes/male1591/", "proxymeshes/proxy741/", "packs/",
)
CMU_RAW = "https://raw.githubusercontent.com/meshula/cmu-mocap/master/data/{sub:03d}/{sub:02d}_{trial:02d}.bvh"
CMU_INDEX = "https://raw.githubusercontent.com/meshula/cmu-mocap/master/cmu-mocap-index-text.txt"
# subject, trial: what the clip is used for (see characters/clips.json)
CMU_CLIPS = [
    (35, 1), (35, 2), (35, 3), (35, 5), (35, 28),  # walks, one subject
    (16, 15), (16, 33),                            # walk; slow walk and stop
    (16, 17), (16, 19),                            # walk and a 90 degree left / right turn
    (18, 8), (19, 8),                              # conversation with hand gestures
    (7, 1),
    (79, 13), (79, 14), (79, 10),                  # mixing batter, making dough, chopping onions (a cook's hands)
    (77, 2), (77, 16), (77, 17), (77, 18),         # standing; laying down on the back and getting up
    (86, 15),                                      # sitting on a chair with hand motions (the commander at his desk)
]


def complete_bvh(path):
    """True when the file holds every frame it declares, each with all its values (a download that
    stops early still ends the stream without an error)."""
    head, _, motion = path.read_text().partition("MOTION")
    channels = sum(int(line.split()[1]) for line in head.splitlines() if line.strip().startswith("CHANNELS"))
    lines = motion.strip().splitlines()
    frames = int(lines[0].split()[1])
    rows = lines[2:]
    return len(rows) == frames and all(len(r.split()) == channels for r in rows)


def fetch(url, dest, expect_sha=None):
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to download from {host}: {url}")
    if dest.exists() and dest.stat().st_size > 0 and (dest.suffix != ".bvh" or complete_bvh(dest)):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.suffix == ".bvh" and not complete_bvh(tmp):
                raise http.client.IncompleteRead(b"", 0)
            break
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as e:
            if attempt == 5:
                raise
            print(f"retry {url}: {e!r}")
            time.sleep(2 + attempt * 2)
    if expect_sha:
        got = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if got != expect_sha:
            tmp.unlink()
            raise ValueError(f"checksum mismatch for {url}: {got}")
    tmp.rename(dest)
    print(f"fetched {dest.relative_to(ROOT)} ({dest.stat().st_size >> 10} KiB)")


def blender_env():
    env = dict(os.environ)
    env["BLENDER_USER_RESOURCES"] = str(VENDOR / "blender" / "res")
    env["BLENDER_USER_EXTENSIONS"] = str(VENDOR / "blender" / "ext")
    return env


def install_mpfb():
    if (VENDOR / "blender" / "ext" / "user_default" / "mpfb" / "__init__.py").exists():
        return
    for sub in ("res", "ext"):
        (VENDOR / "blender" / sub).mkdir(parents=True, exist_ok=True)
    cmd = [BLENDER, "--background", "--factory-startup", "--command", "extension", "install-file",
           "-r", "user_default", "--enable", str(DL / "mpfb-2.0.18.zip")]
    subprocess.run(cmd, check=True, env=blender_env())


def system_assets_dir():
    """MPFB reads asset packs from <extension user dir>/data."""
    return VENDOR / "blender" / "ext" / ".user" / "user_default" / "mpfb" / "data"


class RangeFile(io.RawIOBase):
    """A read-only file over HTTP range requests, so zipfile can pick single entries."""

    def __init__(self, url):
        self.url = url
        head = urllib.request.Request(url, method="HEAD", headers=UA)
        self.size = int(urllib.request.urlopen(head, timeout=60).headers["Content-Length"])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = self.size - self.pos
        if n <= 0:
            return b""
        req = urllib.request.Request(self.url, headers={**UA, "Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        for attempt in range(6):
            try:
                data = urllib.request.urlopen(req, timeout=120).read()
                break
            except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as e:
                if attempt == 5:
                    raise
                print(f"retry range {self.pos}: {e!r}")
                time.sleep(2 + attempt * 2)
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def install_system_assets():
    """Extract the SYSTEM_ASSET_PREFIXES that are not on disk yet (a prefix is there when anything
    under it exists), so a longer list only fetches what it added."""
    dest = system_assets_dir()
    wanted = [p for p in SYSTEM_ASSET_PREFIXES if not any(dest.glob(p + "*"))]
    if not wanted:
        return
    if urllib.parse.urlparse(SYSTEM_ASSETS_URL).hostname not in ALLOWED_HOSTS:
        raise ValueError("system assets host not allowed")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BufferedReader(RangeFile(SYSTEM_ASSETS_URL), 1 << 16)) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.startswith(tuple(wanted)):
                continue
            out = dest / info.filename
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(info))
    print(f"extracted {', '.join(wanted)} into {dest.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-system-assets", action="store_true")
    args = ap.parse_args()
    DL.mkdir(parents=True, exist_ok=True)
    fetch(MPFB_URL, DL / "mpfb-2.0.18.zip", MPFB_SHA)
    install_mpfb()
    fetch(CMU_INDEX, DL / "cmu-index.txt")
    for sub, trial in CMU_CLIPS:
        fetch(CMU_RAW.format(sub=sub, trial=trial), VENDOR / "bvh" / f"{sub:02d}_{trial:02d}.bvh")
    if not args.no_system_assets:
        install_system_assets()


if __name__ == "__main__":
    sys.exit(main())
