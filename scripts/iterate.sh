#!/bin/zsh
# One look iteration: render the main still and three check views, compare to the reference.
# Usage: scripts/iterate.sh            -> next numbered iteration
#        scripts/iterate.sh 3          -> force iteration number
#        GAME_LOCATION=<name> scripts/iterate.sh   -> another location (default courtyard)
#
# Writes renders/iter_NNN.png (Cycles, about 15-20 min, scored against the reference) plus three
# EEVEE checks from the location's layout_preview.json:
#   iter_NNN_scale.png  reference camera with 1.8 m figures
#   iter_NNN_plan.png   top-down floor plan
#   iter_NNN_eye.png    eye level from the courtyard
# Every render goes through the GPU queue (scripts/gpu.py).
set -e
cd "$(dirname "$0")/.."

loc=${GAME_LOCATION:-courtyard}
if [[ -n "$1" ]]; then
  n=$1
else
  last=$(ls renders/iter_[0-9][0-9][0-9].png 2>/dev/null | sed 's/.*iter_0*\([0-9]*\)\.png/\1/' | sort -n | tail -1)
  n=$(( ${last:-0} + 1 ))
fi
iter=$(printf "iter_%03d" "$n")
blender=/Applications/Blender.app/Contents/MacOS/Blender
preview=locations/$loc/layout_preview.json

render() {
  local name=$1; shift
  python3 scripts/gpu.py run --name "$loc/iterate/$name" -- \
    $blender --background --python-exit-code 1 --python scene/build_scene.py -- --location "$loc" "$@" 2>&1 \
    | grep -E "^rendered|^GPU|Error|Traceback"
}

render still --out "renders/${iter}.png"
render scale --out "renders/${iter}_scale.png" --check-scale --layout $preview
render plan --out "renders/${iter}_plan.png" --view plan --check-scale --layout $preview
render eye --out "renders/${iter}_eye.png" --view eye --check-scale --layout $preview
echo "render,${iter} (4 views),,${SECONDS},$(date +%Y-%m-%dT%H:%M:%S)" >> timings.csv

.venv/bin/python scripts/compare.py "renders/${iter}.png" | tee "renders/${iter}.scores.txt"
