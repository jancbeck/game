"""Camera move from the main view down to eye level in the courtyard: a crane descent.

The main view is orthographic and the eye view is a 24 mm perspective camera
(build_scene.camera_ref and camera_eye). Blender cannot blend the two camera
types, so the move uses a perspective camera all the way. At t = 0 it stands
D_START m back along the main view's axis with a long lens that frames the
same width on the ground as the orthographic camera: at that distance the
perspective is too weak to see, and the frame matches the main still.

From there the camera moves in and down, and the lens shortens, so that:

- the distance to the focus point shrinks geometrically from D_START to the
  eye view's distance;
- the framed width at the focus point shrinks geometrically from the main
  view's width to the eye view's width; the lens follows from both;
- the focus point slides from where the main view's axis meets the ground to
  the eye view's target;
- the pitch stays near the main view's 38 deg down while the camera is still
  above the walls, then levels out late in the move.

All of it runs on one smootherstep curve in time, so the move starts and lands
at rest. pose(t) is pure numpy so the soundtrack (orbit_audio.py) can follow
the same path without Blender.
"""

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import location  # noqa: E402

D_START = 400.0          # m: far enough that the long lens looks nearly orthographic
SENSOR = 36.0            # mm, Blender's default sensor width (fit to the image width)
PITCH_LATE = 0.85        # fraction of the move before the pitch levels out: the camera is inside the walls by then
FOCUS_Z = 3.0            # m: height of the plane where the start matches the main frame (wall middles)
MIST_GAIN_TOP = 4.0     # assets/ground_mist.ORTHO_GAIN: the mist gain of the main view
VOLUME_DEPTH = (60.0, 80.0)   # m in front of and behind the focus point where EEVEE computes the haze
_EYE = location.table("views")["eye"]      # build_scene.camera_eye
EYE_POS = tuple(_EYE["location"])
EYE_TARGET = tuple(_EYE["target"])
EYE_LENS = float(_EYE["lens"])


def smootherstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def _direction(yaw, pitch):
    """Unit view vector from yaw (from north toward east) and pitch (up positive), radians."""
    return np.array([math.cos(pitch) * math.sin(yaw), math.cos(pitch) * math.cos(yaw), math.sin(pitch)])


def _ends(res):
    trace = location.load("trace.json")["camera"]
    th, ps, s = math.radians(trace["elevation_deg"]), math.radians(trace["yaw_deg"]), trace["px_per_m"]
    view = _direction(ps, -th)
    right = np.array([math.cos(ps), -math.sin(ps), 0.0])
    up = np.cross(right, view)
    cu, cv = trace["center_px"]
    loc = right * ((res[0] / 2 - cu) / s) + up * ((cv - res[1] / 2) / s) - view * 45.0
    # where the main view's axis meets FOCUS_Z: the long lens matches the frame at that height
    focus0 = loc + view * ((loc[2] - FOCUS_Z) / math.sin(th))
    width0 = res[0] / s
    eye, target = np.array(EYE_POS), np.array(EYE_TARGET)
    d1 = target - eye
    dist1 = float(np.linalg.norm(d1))
    width1 = dist1 * SENSOR / EYE_LENS
    yaw1 = math.atan2(d1[0], d1[1])
    pitch1 = math.asin(d1[2] / dist1)
    return dict(focus=(focus0, target), dist=(D_START, dist1), width=(width0, width1),
                yaw=(ps, yaw1), pitch=(-th, pitch1))


def pose(t, res):
    """Camera at time fraction t: (location (3,), view direction (3,), lens in mm)."""
    e = _ends(res)
    s = smootherstep(t)
    geo = lambda a, b: a * (b / a) ** s
    focus = e["focus"][0] + (e["focus"][1] - e["focus"][0]) * s
    dist = geo(*e["dist"])
    width = geo(*e["width"])
    yaw = e["yaw"][0] + (e["yaw"][1] - e["yaw"][0]) * s
    c = smootherstep((s - PITCH_LATE) / (1 - PITCH_LATE))
    pitch = e["pitch"][0] + (e["pitch"][1] - e["pitch"][0]) * c
    view = _direction(yaw, pitch)
    return focus - view * dist, view, dist * SENSOR / width


class Descent:
    """Poses a perspective camera along the descent; replaces the scene's main camera."""

    def __init__(self, scene, res):
        import bpy
        self.res = res
        self.scene = scene
        data = bpy.data.cameras.new("cam_descent")
        data.sensor_fit = "HORIZONTAL"
        data.sensor_width = SENSOR
        self.cam = bpy.data.objects.new("cam_descent", data)
        scene.collection.objects.link(self.cam)
        scene.camera = self.cam

    def pose(self, t):
        from mathutils import Vector
        loc, view, lens = pose(t, self.res)
        dist = float(np.linalg.norm(loc - np.array(EYE_TARGET)))
        self.cam.location = Vector(loc)
        self.cam.rotation_euler = Vector(view).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = lens
        self.cam.data.clip_start = min(max(0.02 * dist, 0.05), 20.0)
        self.cam.data.clip_end = dist + 400.0
        # EEVEE computes the haze only between these view distances: follow the castle.
        # The ground mist's render handler (assets/ground_mist.py) reads both properties; a steep
        # view crosses less of the thin mist layer, so its gain falls from the main view's to 1.
        self.cam["volume_range"] = (max(0.1, dist - VOLUME_DEPTH[0]), dist + VOLUME_DEPTH[1])
        steep = max(0.0, -view[2]) / math.sin(math.radians(38.0))
        self.cam["mist_gain"] = 1.0 + (MIST_GAIN_TOP - 1.0) * min(steep, 1.0)
        return self.cam.matrix_world.copy()


if __name__ == "__main__":
    res = location.load("layout_preview.json")["render"]["resolution"]
    for t in np.linspace(0, 1, 21):
        loc, view, lens = pose(t, res)
        pitch = math.degrees(math.asin(view[2]))
        print(f"t={t:.2f}  cam=({loc[0]:7.2f},{loc[1]:7.2f},{loc[2]:7.2f})  pitch={pitch:6.1f}  lens={lens:7.1f}")
