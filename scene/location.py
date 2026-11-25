"""The location a run builds, and the files that describe it.

A location is a folder `locations/<name>/`:

    plan.json            the place in metres: blocks, platform, props, mounted parts, crows
    trace.json           the main orthographic camera
    layout.json          the Cycles look: light, exposure, post, rain
    layout_preview.json  the EEVEE look for previews and videos
    location.json        tables that are not geometry: check-view cameras, light-group names,
                         crow perch names, fire simulations and hotspots

Shared code in scene/ reads these files only through this module, so the same code builds any
location. The location of a run is `--location <name>` among the script arguments after `--`,
else the GAME_LOCATION environment variable, else `courtyard`.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCATIONS = ROOT / "locations"
DEFAULT = "courtyard"


def _from_argv(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    for i, a in enumerate(args):
        if a == "--location" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--location="):
            return a.split("=", 1)[1]
    return None


_name = _from_argv(sys.argv) or os.environ.get("GAME_LOCATION") or DEFAULT
_override = {}   # file name -> path given on the command line (build_scene --plan)
_text = {}       # path -> file text, read once per run


def name():
    return _name


def use(location):
    """Switch the run to another location (scripts call this with their --location argument)."""
    global _name
    if location and location != _name:
        _name = location
        _text.clear()


def add_argument(ap):
    """The --location option every script accepts."""
    ap.add_argument("--location", default=_name, help="folder under locations/ (default %(default)s)")


def folder(location=None):
    return LOCATIONS / (location or _name)


def path(fname):
    """Path of one of the location's files, or the file given in its place with override()."""
    return Path(_override.get(fname) or folder() / fname)


def override(fname, file_path):
    _override[fname] = Path(file_path)


def load(fname):
    """The location's JSON file as a new object on every call (callers may change it)."""
    p = path(fname)
    if p not in _text:
        _text[p] = p.read_text()
    return json.loads(_text[p])


def plan():
    return load("plan.json")


def table(key):
    """One table of location.json."""
    return load("location.json")[key]


def game_dir(location=None):
    """Where the game export of a location goes: game/ for the first location (`DEFAULT`),
    game/locations/<name>/ for every other one, with the same layout (assets/, data/, build/)."""
    name = location or _name
    return ROOT / "game" if name == DEFAULT else ROOT / "game" / "locations" / name


def rel_prefix(location=None):
    """Prefix of this location's files in scene.json, whose paths are relative to game/."""
    name = location or _name
    return "" if name == DEFAULT else f"locations/{name}/"
