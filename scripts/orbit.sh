#!/bin/zsh
# Render a camera move (the 360 degree turn of the main camera, or the descent to eye level)
# and encode it with its soundtrack.
# Usage: scripts/orbit.sh [render_orbit.py options]
#   scripts/orbit.sh                              -> 480 frames, 20 s, main render size -> renders/orbit.mp4
#   scripts/orbit.sh --frames 240                 -> 12 fps rendered, each frame shown twice
#   scripts/orbit.sh --move descent               -> 384 frames, 16 s, main view down to eye level -> renders/descent.mp4
#   scripts/orbit.sh --out-dir renders/orbit_test --frames 25 --even-yaw --res 768 512
#                                                 -> preview, one frame every 15 deg, renders/orbit_test.mp4
#
# Frames already in the output folder are skipped, so an interrupted run resumes
# where it stopped. Delete the folder (or pass --overwrite) after changing the scene.
# Writes <out-dir>/frame_NNNN.png, <out-dir>/orbit.wav and <out-dir>.mp4. The render goes through
# the GPU queue (scripts/gpu.py).
set -e
cd "$(dirname "$0")/.."

args=("$@")
move=orbit
for (( i = 1; i <= $#args; i++ )); do
  [[ $args[i] == --move ]] && move=$args[i+1]
done
if [[ $move == descent ]]; then
  out_dir=renders/descent; frames=384; duration=16
else
  out_dir=renders/orbit; frames=480; duration=20
fi
for (( i = 1; i <= $#args; i++ )); do
  case $args[i] in
    --out-dir)  out_dir=$args[i+1] ;;
    --frames)   frames=$args[i+1] ;;
    --duration) duration=$args[i+1] ;;
  esac
done

blender=/Applications/Blender.app/Contents/MacOS/Blender
python3 scripts/gpu.py run --name "${GAME_LOCATION:-courtyard}/video/${move}" -- \
  $blender --background --python-exit-code 1 --python scene/render_orbit.py -- "$@" 2>&1 \
  | grep --line-buffered -E "^ORBIT|^GPU|Traceback|Error:" | grep --line-buffered -v "Not freed memory"
echo "render,${move} ${frames} frames,,${SECONDS},$(date +%Y-%m-%dT%H:%M:%S)" >> timings.csv

# the rendered rate is frames / duration; the output is always 24 fps, so a
# lower rendered rate repeats frames instead of stretching the turn
ffmpeg -y -loglevel error \
  -framerate "${frames}/${duration}" -i "${out_dir}/frame_%04d.png" \
  -i "${out_dir}/orbit.wav" \
  -map 0:v -map 1:a -r 24 -t "$duration" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 192k \
  "${out_dir}.mp4"
echo "encoded -> ${out_dir}.mp4"
