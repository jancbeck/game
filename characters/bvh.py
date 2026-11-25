"""A small BVH reader and forward kinematics, with no Blender dependency (mathutils is optional).

The CMU files (Bruce Hahne's MotionBuilder-friendly conversion) use Y up, +Z forward in the T
pose on frame 0, rotation channels in Z Y X order, and units of about 1/0.0564 m.
"""

import math
import re

CMU_UNIT_M = 0.0564  # metres per BVH unit (CMU skeletons: a thigh of 7.4 units is 0.42 m)


class Bvh:
    def __init__(self):
        self.names = []
        self.parent = []
        self.offset = []
        self.channels = []
        self.end_offset = {}      # joint name -> offset of its End Site child
        self.frames = []          # one list of floats per frame
        self.dt = 1.0 / 120.0

    @property
    def fps(self):
        return 1.0 / self.dt


def parse(path):
    text = open(path).read()
    head, motion = text.split("MOTION")
    bvh = Bvh()
    stack = []
    tokens = re.findall(r"[{}]|[^\s{}]+", head)
    i = 0
    cur = None
    while i < len(tokens):
        t = tokens[i]
        if t in ("ROOT", "JOINT"):
            name = tokens[i + 1]
            bvh.names.append(name)
            bvh.parent.append(stack[-1] if stack else -1)
            bvh.offset.append(None)
            bvh.channels.append([])
            cur = len(bvh.names) - 1
            i += 2
        elif t == "End":
            # End Site { OFFSET x y z }
            j = i + 3
            assert tokens[j] == "OFFSET"
            bvh.end_offset[bvh.names[stack[-1]]] = tuple(float(x) for x in tokens[j + 1:j + 4])
            i = j + 5
        elif t == "{":
            stack.append(cur)
            i += 1
        elif t == "}":
            cur = stack.pop()
            i += 1
        elif t == "OFFSET":
            bvh.offset[cur] = tuple(float(x) for x in tokens[i + 1:i + 4])
            i += 4
        elif t == "CHANNELS":
            n = int(tokens[i + 1])
            bvh.channels[cur] = tokens[i + 2:i + 2 + n]
            i += 2 + n
        else:
            i += 1
    lines = motion.strip().splitlines()
    n_frames = int(lines[0].split()[1])
    bvh.dt = float(lines[1].split()[2])
    for ln in lines[2:2 + n_frames]:
        bvh.frames.append([float(x) for x in ln.split()])
    return bvh


def _rot(axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    if axis == "X":
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == "Y":
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def fk(bvh, frame):
    """{joint name: (3x3 world rotation, world position)} for one frame, in BVH axes and units."""
    values = bvh.frames[frame]
    out = {}
    cursor = 0
    for idx, name in enumerate(bvh.names):
        pos_local = list(bvh.offset[idx])
        rot = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        for ch, val in zip(bvh.channels[idx], values[cursor:cursor + len(bvh.channels[idx])]):
            axis = ch[0]
            if ch.endswith("position"):
                pos_local["XYZ".index(axis)] += val
            else:
                rot = _mul(rot, _rot(axis, math.radians(val)))
        cursor += len(bvh.channels[idx])
        p = bvh.parent[idx]
        if p < 0:
            out[name] = (rot, pos_local)
        else:
            prot, ppos = out[bvh.names[p]]
            d = _mv(prot, pos_local)
            out[name] = (_mul(prot, rot), [ppos[k] + d[k] for k in range(3)])
    return out
