"""Render a 360 degree turn of the main camera around the courtyard, with its soundtrack.

    Blender --background --python scene/render_orbit.py -- [options]

The scene is built once by build_scene.main() with the default `ref` view;
this script then turns that camera and redraws the rain, and renders all
frames in the same Blender process.

Camera: the `ref` camera (orthographic, 38 deg elevation, trace.json) at the
main render's resolution turns 360 deg counter-clockwise around a vertical
axis through the courtyard centre PIVOT (location.json views.centre), keeping elevation and distance. The
first and last frame are the main render's framing. The yaw follows a
smootherstep curve: it starts and lands at rest, with no step in speed or
acceleration. Mid-turn the frame eases (weight sin^2(pi t)) to centre on the
pivot and zooms out by up to ZOOM_OUT, so the castle swings around the image
centre; wall edges and tower corners may leave the frame at some angles.
A slow drift of a few cm and a fraction of a degree, windowed to zero at both
ends, keeps the move from looking mechanical.

Rain: build_scene.build_rain makes the streak and splash objects with quads
facing one fixed yaw. Before every frame their meshes are rebuilt here facing
the camera, from a fresh random draw seeded by the frame index. Real streaks
fall about one streak length per 1/24 s, so independent draws read as rain.

Sound (--audio-only, or after the render): scene/orbit_audio.py mixes it from
the Stable Audio 3 clips, heard from this camera's 3D position along the turn:
a distant rain bed and sources placed in the courtyard, with distance, delay,
air absorption, pan and courtyard reverb.

Descent (--move descent): instead of the turn, the camera cranes from the main
view down to eye level in the courtyard (scene/descent.py). It ends on the
`eye` check view. Defaults change to renders/descent, 384 frames, 16 s.

Options:
  --move orbit|descent the camera move (default orbit)
  --out-dir DIR        frames go to DIR/frame_NNNN.png, sound to DIR/orbit.wav
  --frames N           frames in the turn (default 480); the last one equals the first
  --even-yaw           space frames evenly in angle, not time (previews: --frames 25 = every 15 deg)
  --duration S         seconds (default 20); fps = N / S
  --res W H            resolution (default: layout.json, the main render's size);
                       a different aspect changes the framing
  --only i,j,..        render only these frame indices
  --layout PATH        render layout (default: the location's layout_preview.json, the EEVEE look;
                       Cycles per frame is too slow for a video)
  --samples N          EEVEE render samples (default 32, half of layout.json: the
                       per-frame rain draw and the Kuwahara pass hide the extra noise)
  --volume-samples N   haze volume samples (default: layout.json)
  --no-raytracing      turn EEVEE raytracing off
  --overwrite          re-render frames that already exist (default: skip them)
  --audio-only         mix the soundtrack, render nothing
  --no-anim            leave fire, windows, crows and trees still (scene/anim.py is not set up)
"""

import argparse
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import location  # noqa: E402
import orbit_audio  # noqa: E402
from descent import smootherstep  # noqa: E402

PIVOT = tuple(location.table("views")["centre"])
CAM_DIST = 45.0         # camera_ref's distance along the view axis
DRIFT_POS = 0.05        # m, peak camera drift
DRIFT_TILT = 0.25       # deg, peak camera tilt drift
ZOOM_OUT = 0.12         # mid-turn ortho_scale increase, eased in and out
SEED = 11
NEAR_CLEAR = 1.5        # m: no rain streaks closer than this to the camera


# ---------- camera move ----------

def yaw_deg(t):
    """Turn angle at time fraction t (0..1): at rest at both ends."""
    return 360.0 * smootherstep(min(max(t, 0.0), 1.0))


def drift(t):
    """Smooth low-frequency offsets (dx, dy, dz in m; tilt, roll in deg), zero at t = 0 and 1."""
    w = math.sin(math.pi * t) ** 2
    rng = np.random.default_rng(SEED)
    out = []
    for amp in (DRIFT_POS, DRIFT_POS, DRIFT_POS * 0.6, DRIFT_TILT, DRIFT_TILT * 0.4):
        f = rng.uniform(0.6, 1.6, 2)          # cycles per turn
        ph = rng.uniform(0, 2 * math.pi, 2)
        v = 0.6 * math.sin(2 * math.pi * f[0] * t + ph[0]) + 0.4 * math.sin(2 * math.pi * f[1] * t + ph[1])
        out.append(amp * w * v)
    return out


def frame_time(i, args):
    """Time fraction of frame i; with --even-yaw, the time at which yaw is 360 * i / (N - 1)."""
    u = i / (args.frames - 1)
    if not args.even_yaw:
        return u
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if smootherstep(mid) < u else (lo, mid)
    return (lo + hi) / 2


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--move", choices=("orbit", "descent"), default="orbit")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--frames", type=int, default=None)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--res", type=int, nargs=2, default=None)
    ap.add_argument("--even-yaw", action="store_true")
    ap.add_argument("--only", default=None)
    location.add_argument(ap)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--volume-samples", type=int, default=None)
    ap.add_argument("--no-raytracing", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--no-anim", action="store_true")
    args = ap.parse_args(argv)
    location.use(args.location)
    args.layout = args.layout or str(location.path("layout_preview.json"))
    defaults = {"orbit": ("orbit", 480, 20.0), "descent": ("descent", 384, 16.0)}[args.move]
    args.out_dir = args.out_dir or str(ROOT / "renders" / defaults[0])
    args.frames = args.frames or defaults[1]
    args.duration = args.duration or defaults[2]
    return args


# ---------- scene ----------

def build(args):
    """Run build_scene.main() without its still render; return the rain inputs it used."""
    import bpy
    import build_scene as bs

    captured = {}
    build_rain, render = bs.build_rain, bs.render

    def capture_rain(spec, cam_yaw_deg, platform, mats, rng, clear=None):
        captured.update(spec=spec, platform=platform)
        build_rain(spec, cam_yaw_deg, platform, mats, rng, clear)

    class _Ops:
        render = SimpleNamespace(render=lambda **kw: None)

        def __getattr__(self, name):
            return getattr(bpy.ops, name)

    class _NoRender:
        ops = _Ops()

        def __getattr__(self, name):
            return getattr(bpy, name)

    def settings_only(out_path, spec, passes=False):
        # build_scene.render applies the render settings, then renders; keep only the settings
        bs.bpy = _NoRender()
        try:
            render(out_path, spec)
        finally:
            bs.bpy = bpy

    bs.build_rain, bs.render = capture_rain, settings_only
    sys.argv = [sys.argv[0], "--", "--out", str(Path(args.out_dir) / "_unused.png"), "--layout", args.layout,
                "--location", location.name()]
    bs.main()
    bs.build_rain, bs.render = build_rain, render
    return captured


class Turn:
    """Poses the main camera along the turn."""

    def __init__(self, cam):
        import bpy
        from mathutils import Vector
        bpy.context.view_layer.update()
        self.cam = cam
        self.base = cam.matrix_world.copy()
        self.ref_scale = cam.data.ortho_scale
        # the pivot in the camera's image plane, in m right and up of the image centre
        local = self.base.inverted() @ Vector((PIVOT[0], PIVOT[1], 0.0))
        self.pivot_offset = (local.x, local.y)

    def pose(self, t, with_drift=True):
        """Set the camera at time fraction t; returns its world matrix."""
        from mathutils import Matrix, Vector
        p = Vector((PIVOT[0], PIVOT[1], 0.0))
        rot = Matrix.Translation(p) @ Matrix.Rotation(math.radians(yaw_deg(t)), 4, "Z") @ Matrix.Translation(-p)
        m = rot @ self.base
        w = math.sin(math.pi * t) ** 2
        # re-centre: slide the camera in its image plane until the pivot is at the image centre mid-turn
        m = m @ Matrix.Translation(Vector((self.pivot_offset[0] * w, self.pivot_offset[1] * w, 0.0)))
        if with_drift:
            dx, dy, dz, tilt, roll = drift(t)
            loc, q, _ = m.decompose()
            local = q.to_matrix().to_4x4()
            local = local @ Matrix.Rotation(math.radians(tilt), 4, "X") @ Matrix.Rotation(math.radians(roll), 4, "Z")
            m = Matrix.Translation(loc + Vector((dx, dy, dz))) @ local
        self.cam.matrix_world = m
        self.cam.data.ortho_scale = self.ref_scale * (1 + ZOOM_OUT * w)
        return m


class Rain:
    """Re-draws the streak and splash meshes of build_rain, facing a given view direction."""

    def __init__(self, spec, platform):
        import bpy
        self.spec = spec
        self.layers = spec.get("layers", [[1.0, 1.0, 1.0, 1.0]])
        self.objects = [bpy.data.objects[f"rain_{i}"] for i in range(len(self.layers))]
        self.splashes = bpy.data.objects["splashes"]
        self.platform = np.array(platform, dtype=float)
        self.sheltered = np.array(spec.get("sheltered", []), dtype=float).reshape(-1, 3, 2)

    def update(self, view, seed, cam=None):
        s = self.spec
        rng = np.random.default_rng(seed)
        view = np.array(view, dtype=float)
        lo = np.array([r[0] for r in s["region"]], dtype=float)
        hi = np.array([r[1] for r in s["region"]], dtype=float)
        wind = np.array([*s.get("wind", (0.0, 0.0)), -1.0])
        wind /= np.linalg.norm(wind)
        lmin, lmax = s["length"]
        # side vector across a streak, perpendicular to the (orthographic) view
        across = np.cross(wind, view)
        across /= np.linalg.norm(across)
        for ob, (share, _bright, lscale, wscale) in zip(self.objects, self.layers):
            n = int(s["count"] * share)
            p = rng.uniform(lo, hi, size=(n, 3))
            keep = np.ones(n, bool)
            for box in self.sheltered:
                keep &= ~np.all((p > box[:, 0]) & (p < box[:, 1]), axis=1)
            if cam is not None:
                # no streaks right in front of the lens at eye level
                keep &= np.linalg.norm(p - cam, axis=1) > NEAR_CLEAR
            p = p[keep]
            n = len(p)
            d = wind * (rng.uniform(lmin, lmax, n) * lscale)[:, None]
            side = across * (s["width"] * wscale * rng.uniform(0.6, 1.4, n) / 2)[:, None]
            verts = np.stack([p + side, p - side, p + d - side * 0.3, p + d + side * 0.3], axis=1)
            self._replace(ob, verts.reshape(-1, 3), 4)

        # splashes: 3-6 upward flecks per impact, as in build_rain
        n = s.get("splashes", 0)
        xy = rng.uniform(lo[:2], hi[:2], size=(n, 2))
        import terrain
        outside = np.array([terrain.ground_z(x, y) for x, y in xy])
        z = np.where(_inside(xy, self.platform), 0.0, outside) + 0.005
        c = np.repeat(np.column_stack([xy, z]), rng.integers(3, 7, n), axis=0)
        m = len(c)
        a = rng.uniform(0, 2 * math.pi, m)
        out = np.column_stack([np.cos(a), np.sin(a), np.zeros(m)])
        h = rng.uniform(0.04, 0.10, m)[:, None]
        tip = c + out * h * 0.6 + np.array([0, 0, 1.0]) * h
        side = np.cross([0, 0, 1.0], view)
        side *= 0.006 / np.linalg.norm(side)
        base = c + out * 0.02
        verts = np.stack([base + side, base - side, tip], axis=1)
        self._replace(self.splashes, verts.reshape(-1, 3), 3)

    @staticmethod
    def _replace(ob, co, per_face):
        import bpy
        old = ob.data
        me = bpy.data.meshes.new(old.name)
        me.vertices.add(len(co))
        me.vertices.foreach_set("co", co.astype(np.float32).ravel())
        me.loops.add(len(co))
        me.loops.foreach_set("vertex_index", np.arange(len(co), dtype=np.int32))
        me.polygons.add(len(co) // per_face)
        me.polygons.foreach_set("loop_start", np.arange(0, len(co), per_face, dtype=np.int32))
        me.update()
        for mat in old.materials:
            me.materials.append(mat)
        ob.data = me
        bpy.data.meshes.remove(old)


def _inside(xy, poly):
    """Even-odd point-in-polygon for an (n, 2) array."""
    x, y = xy[:, 0], xy[:, 1]
    inside = np.zeros(len(xy), bool)
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        if ay == by:
            continue
        inside ^= ((ay > y) != (by > y)) & (x < ax + (y - ay) * (bx - ax) / (by - ay))
    return inside


def render_frames(args):
    import bpy
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    captured = build(args)
    sc = bpy.context.scene
    framed_res = (sc.render.resolution_x, sc.render.resolution_y)   # the main camera is framed for this size
    if args.res:
        sc.render.resolution_x, sc.render.resolution_y = args.res
    sc.render.resolution_percentage = 100
    turn = Turn(sc.camera)
    if args.move == "descent":
        import descent
        mover = descent.Descent(sc, framed_res)
    else:
        mover = turn
    if args.samples:
        sc.eevee.taa_render_samples = args.samples
    if args.volume_samples:
        sc.eevee.volumetric_samples = args.volume_samples
    if args.no_raytracing and hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = False
    sc.render.image_settings.file_format = "PNG"
    rain = Rain(captured["spec"], captured["platform"]) if captured.get("spec") else None
    # ambient motion from scene/anim.py, posed from the frame's time in seconds
    motion = None
    if not args.no_anim:
        import anim
        import build_scene as bs
        motion = anim
        print(f"ORBIT anim {anim.setup(perches=bs.PERCHES)}", flush=True)
    print(f"ORBIT built in {time.time() - t0:.1f}s; ortho_scale={turn.ref_scale:.2f} m at the ends, "
          f"{turn.ref_scale * (1 + ZOOM_OUT):.2f} m mid-turn; samples={sc.eevee.taa_render_samples} "
          f"volume_samples={sc.eevee.volumetric_samples} raytracing={getattr(sc.eevee, 'use_raytracing', None)} "
          f"res={sc.render.resolution_x}x{sc.render.resolution_y}", flush=True)

    todo = [int(i) for i in args.only.split(",")] if args.only else list(range(args.frames))
    t_frames, done = time.time(), 0
    for k, i in enumerate(todo):
        path = out_dir / f"frame_{i:04d}.png"
        if path.exists() and not args.overwrite:
            continue
        t = time.time()
        m = mover.pose(frame_time(i, args))
        if rain:
            rain.update(-np.array(m)[:3, 2], SEED * 100003 + i, cam=np.array(m)[:3, 3])
        if motion:
            motion.apply(frame_time(i, args) * args.duration)
        sc.frame_set(i + 1)
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        done += 1
        left = (time.time() - t_frames) / done * (len(todo) - k - 1)
        print(f"ORBIT frame {i} {time.time() - t:.1f}s -> {path.name}, about {left / 60:.0f} min left", flush=True)
    print(f"ORBIT done in {time.time() - t0:.1f}s", flush=True)


def main():
    args = parse_args()
    if not args.audio_only:
        render_frames(args)
    orbit_audio.write_mix(Path(args.out_dir).resolve() / "orbit.wav", args.frames, args.duration, move=args.move)


if __name__ == "__main__":
    main()
