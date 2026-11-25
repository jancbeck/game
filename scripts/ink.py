#!/usr/bin/env python3
"""Compile the game's Ink story: game/data/story/main.ink (with its INCLUDEs) -> main.json, and the
fixture game/tests/checks.ink that systems_check.gd plays -> checks.json.

    scripts/ink.py            compile
    scripts/ink.py --check    compile to a temporary file and fail when a compiled story is out of date

inklecate (https://github.com/inkle/ink/releases, inklecate_mac.zip) is found through $INKLECATE,
PATH or ~/.cache/inklecate/inklecate. The binary is not part of the repository.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORY = ROOT / "game" / "data" / "story"
TESTS = ROOT / "game" / "tests"
# (source, compiled) of every story the game or its checks read
TARGETS = [(STORY / "main.ink", STORY / "main.json"), (TESTS / "checks.ink", TESTS / "checks.json")]


def find_inklecate():
    for cand in (os.environ.get("INKLECATE"), shutil.which("inklecate"), Path.home() / ".cache/inklecate/inklecate"):
        if cand and Path(cand).is_file():
            return str(cand)
    return None


def compile_to(exe, out, src=STORY / "main.ink"):
    r = subprocess.run([exe, "-o", str(out), str(src)], capture_output=True, text=True, cwd=src.parent)
    text = (r.stdout + r.stderr).strip()
    problems = [ln for ln in text.splitlines() if ln.startswith(("ERROR", "WARNING"))]
    return r.returncode == 0 and not any(p.startswith("ERROR") for p in problems), problems


def stale(exe=None):
    """Problems with the compiled stories: [] when each .json matches its sources (or no inklecate to tell)."""
    exe = exe or find_inklecate()
    if exe is None:
        return []
    for src, target in TARGETS:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / target.name
            ok, problems = compile_to(exe, out, src)
            if not ok:
                return [f"ink: {p}" for p in problems] or ["ink: inklecate failed"]
            if not target.exists() or target.read_bytes() != out.read_bytes():
                return [f"ink: {target.relative_to(ROOT)} is out of date; run scripts/ink.py"]
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    exe = find_inklecate()
    if exe is None:
        print("inklecate not found: set $INKLECATE or put it on PATH or in ~/.cache/inklecate/", file=sys.stderr)
        return 2
    if args.check:
        probs = stale(exe)
        print("\n".join(probs) or "ink: the compiled stories are up to date")
        return 1 if probs else 0
    status = 0
    for src, target in TARGETS:
        ok, problems = compile_to(exe, target, src)
        print("\n".join(problems))
        print(f"compiled {target.relative_to(ROOT)}" if ok else f"compile failed: {src.relative_to(ROOT)}")
        status |= 0 if ok else 1
    return status


if __name__ == "__main__":
    sys.exit(main())
