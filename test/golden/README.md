# Golden screenshots

Reference frames for the visual regression check (`tools/compare_goldens.gd`,
run in the `screenshots` CI job). Each `<name>.png` here is compared against the
freshly rendered `screenshots/<name>.png` with a tolerant perceptual metric;
CI fails when a frame drifts too far (a darkened scene, a mis-placed character,
broken occlusion). See `docs/CI.md` for the metric and thresholds.

## Updating goldens (after an intentional visual change)

There is no GPU in the dev sandbox, so goldens must be captured from a CI
render (llvmpipe), not generated locally:

1. Let the PR's `screenshots` job run — it force-pushes the frames to the
   `ci-screenshots` branch.
2. Fetch them into `screenshots/` and accept:
   ```sh
   git fetch origin ci-screenshots
   rm -rf screenshots && git checkout origin/ci-screenshots -- . && mv *.png screenshots/ 2>/dev/null || true
   godot --headless -s tools/compare_goldens.gd -- --update
   ```
   (or copy the PNGs into `test/golden/` by hand — they are plain images.)
3. Commit the updated `test/golden/*.png` in the same PR as the visual change,
   so the diff shows exactly what moved.
