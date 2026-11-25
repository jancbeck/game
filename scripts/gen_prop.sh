#!/bin/zsh
# Generate a textured 3D mesh for one prop crop with Trellis.2 (MLX).
# Usage: scripts/gen_prop.sh gallows [extra mlx-spatial flags...]
# Output: props/meshes/<name>.glb
set -e
cd "$(dirname "$0")/.."
name=$1; shift || true

.venv/bin/mlx-spatial-trellis2 --root weights/trellis2 generate-textured \
  weights/trellis2 "props/crops/${name}_rgba.png" \
  --output "outputs/${name}.glb" \
  --pipeline-type 512 \
  --dino-root weights/trellis2/dinov3 \
  --rmbg-root weights/trellis2/rmbg \
  "$@"
mkdir -p props/meshes
mv outputs/"${name}".glb "props/meshes/${name}.glb"
echo "-> props/meshes/${name}.glb"
# log wall time; columns: step,name,estimate_s,actual_s,finished
echo "gen_prop,${name},,${SECONDS},$(date +%Y-%m-%dT%H:%M:%S)" >> timings.csv
