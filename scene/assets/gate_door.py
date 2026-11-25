"""Castle gate passage seen from inside the courtyard: stone portals, barrel vault, portcullis, plank doors.

Origin: bottom center of the opening at ground level, on the inner wall face. The wall face is the
XZ plane at y = 0 and +Y points into the wall (the gatehouse is 3.6 m deep, so the outer face is at
y = 3.6). The prop is placed at the inner wall face of the gatehouse.

Passage: 3.0 m wide, straight sides to 3.0 m, a half-circle vault to 4.5 m, running the full depth
of the gatehouse. The curtain wall behind the gatehouse is solid, so the block's own cut does not
reach through it: build() cuts the passage, the portcullis slot and the murder holes out of the
blocks named in CUT_BLOCKS (the gatehouse and the north curtain wall behind it). The cutters are
hidden objects parented to the prop root, so the cut follows the prop wherever it is placed.
Without those blocks (prop preview) nothing is cut.

From the courtyard side, front to back:

- y -0.09 to 0.45: dressed arch ring with keystone, jamb stones, imposts and a worn threshold.
- y 0.50 to 0.78: portcullis slot. The grille is raised, its spiked lower edge hangs in the crown
  of the vault, and the grooves for its guides run down both walls.
- y 0.92 to 1.18: two murder holes in the vault, framed by dressed stones.
- y 1.30 to 1.80: second dressed arch, narrower than the vault. The two plank leaves hang in it
  and are barred.
- y 1.05: a torch burns in an iron sconce on the east side wall, between the portcullis slot and
  the doors, with years of soot above it. It is the porter's light and the only flame in the passage.
- y 1.80 to 3.6: the passage goes on to the outer face, where a mirrored portal closes it.

The floor is dressed flagstones worn into cart ruts and a footpath dish.
"""

import math

import bpy

HALF = 1.5            # half the passage width, also the vault radius
SPRING = 3.0          # height where the vault starts
PASSAGE = 3.6         # depth of the gatehouse: y of the outer face
VOUSSOIRS = 15

FRONT = 0.09          # portal stones stand this far proud of the wall face
BACK = 0.45           # back face of the portal stones
RING = 0.40           # radial depth of the arch ring
FIT = 0.01            # portal stones overlap the cut by this much, so no face is coplanar with it
KEY_SPAN = 0.085      # keystone angle as a share of the half circle

DOOR_Y = 1.45         # front face of the plank leaves
DOOR_R = 1.32         # opening of the door arch: the leaves fill a half circle of this radius
SLOT_Y = 0.64         # center of the portcullis slot
SLOT_W = 0.28         # slot thickness along y
HOLE_Y = 1.05         # center of the murder holes along y
HOLE_X = 0.50         # murder holes sit this far either side of the axis
HOLE = 0.26           # murder hole side
CUT_BLOCKS = ("block_gatehouse", "block_north_curtain")   # the masonry the passage runs through
TORCH_Y = 1.05        # passage torch: along the passage, on the east side wall
TORCH_Z = 1.95        # mount height of its sconce
TORCH_SCALE = 1.2
TORCH_WATTS = 120.0   # the torch light; a low fill on the floor in front of the doors goes with it

LIGHTS = []


def _dressed(mat):
    """Copy of the wall material with `dressed` on: one chiseled stone per piece, paler than the rubble."""
    copy = bpy.data.materials.get("stone_dressed")
    if copy is None:
        copy = mat.copy()
        copy.name = "stone_dressed"
        copy.node_tree.nodes["dressed"].outputs[0].default_value = 1.0
    return copy


# ---------- masonry ----------

def _wedge(kit, name, a0, a1, r0, r1, y0, y1, mat, parent, cx=0.0):
    """Arch stone between angles a0..a1 (radians, measured from +X) and radii r0..r1."""
    verts = []
    for a in (a0, a1):
        for r in (r0, r1):
            for y in (y0, y1):
                verts.append((cx + r * math.cos(a), y, SPRING + r * math.sin(a)))
    v = lambda i, j, k: i * 4 + j * 2 + k  # noqa: E731
    faces = [
        (v(0, 0, 0), v(0, 1, 0), v(0, 1, 1), v(0, 0, 1)),
        (v(1, 0, 0), v(1, 0, 1), v(1, 1, 1), v(1, 1, 0)),
        (v(0, 0, 0), v(0, 0, 1), v(1, 0, 1), v(1, 0, 0)),
        (v(0, 1, 0), v(1, 1, 0), v(1, 1, 1), v(0, 1, 1)),
        (v(0, 0, 0), v(1, 0, 0), v(1, 1, 0), v(0, 1, 0)),
        (v(0, 0, 1), v(0, 1, 1), v(1, 1, 1), v(1, 0, 1)),
    ]
    return kit.mesh(name, verts, faces, mat=mat, parent=parent, bevel=0.018)


def _arch(kit, stone, root, tag, r_in, ring, y0, y1, rng, n=VOUSSOIRS, keystone=False):
    """Half-circle arch ring of `n` stones from the +X springing to the -X one.

    With `keystone` the middle stone is wider, taller and stands further out (y0 - 0.05).
    """
    key = n // 2
    key_span = KEY_SPAN * math.pi if keystone else 0.0
    span = (math.pi - key_span) / (n - (1 if keystone else 0))
    gap = 0.010
    a0 = 0.0
    for i in range(n):
        is_key = keystone and i == key
        w = key_span if is_key else span
        r1 = r_in + (ring + 0.15 if is_key else ring + (0.03 if i % 2 else 0.0))
        front = y0 - 0.05 if is_key else y0
        _wedge(kit, f"{tag}_voussoir_{i}", a0 + gap, a0 + w - gap, r_in + kit.jitter(rng, 0.004), r1,
               front, y1, stone, root)
        a0 += w


def _jambs(kit, stone, root, tag, x_in, top, y0, y1, rng, courses=7):
    """Jamb stones in alternating widths (long-and-short work) up to height `top`."""
    base = top / courses
    for side in (-1, 1):
        z = 0.0
        for c in range(courses):
            h = base + kit.jitter(rng, 0.04) if c < courses - 1 else top - z
            width = (0.38 if c % 2 == 0 else 0.58) + kit.jitter(rng, 0.02)
            kit.box(f"{tag}_jamb_{'R' if side > 0 else 'L'}{c}",
                    (width, y1 - y0, h - 0.03),
                    (side * (x_in + width / 2), (y0 + y1) / 2, z + h / 2),
                    mat=stone, bevel=0.018, parent=root)
            z += h


def _portal(kit, mats, rng, root, tag, front_y, back_y):
    """Dressed arch ring, jambs and imposts that frame the passage mouth."""
    stone = _dressed(mats["stone_wall"])
    r_in = HALF - FIT
    _arch(kit, stone, root, tag, r_in, RING, front_y, back_y, rng, keystone=True)
    _jambs(kit, stone, root, tag, r_in, SPRING - 0.2, front_y, back_y, rng)
    for side in (-1, 1):
        w = 0.65
        kit.box(f"{tag}_impost_{'R' if side > 0 else 'L'}", (w, back_y - front_y + 0.07, 0.16),
                (side * (HALF - 0.09 + w / 2), (front_y - 0.07 + back_y) / 2, SPRING - 0.08),
                mat=stone, bevel=0.02, parent=root)


def _door_arch(kit, mats, rng, root):
    """Narrower dressed arch that carries the doors, set deep in the passage."""
    stone = _dressed(mats["stone_wall"])
    y0, y1 = DOOR_Y - 0.17, DOOR_Y + 0.35
    _arch(kit, stone, root, "door", DOOR_R, HALF - DOOR_R + 0.22, y0, y1, rng, n=13)
    _jambs(kit, stone, root, "door", DOOR_R, SPRING, y0, y1, rng, courses=6)
    # raised sill under the leaves
    _slab(kit, "door_sill", -HALF - 0.05, HALF + 0.05, y0 - 0.05, y1 + 0.05, 0.11, stone, root, rng,
          thick=0.2, wear=lambda x, y: 0.05 * math.exp(-(x / 0.9) ** 2), nx=10, ny=2)


# ---------- floor ----------

def _slab(kit, name, x0, x1, y0, y1, top, mat, parent, rng, thick=0.08, wear=None, nx=5, ny=2, tilt=0.0):
    """Flagstone with a worn top: `wear(x, y)` lowers the top surface, `tilt` rocks it a little."""
    verts, faces = [], []
    tx, ty = kit.jitter(rng, tilt), kit.jitter(rng, tilt)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            z = top + tx * (x - cx) + ty * (y - cy) - (wear(x, y) if wear else 0.0)
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    ring = ([(i, 0) for i in range(nx)] + [(nx, j) for j in range(ny)]
            + [(i, ny) for i in range(nx, 0, -1)] + [(0, j) for j in range(ny, 0, -1)])
    zb = top - thick
    base = len(verts)
    for i, j in ring:
        x, y, _ = verts[j * (nx + 1) + i]
        verts.append((x, y, zb))
    m = len(ring)
    for k in range(m):
        i0, j0 = ring[k]
        i1, j1 = ring[(k + 1) % m]
        faces.append((j0 * (nx + 1) + i0, base + k, base + (k + 1) % m, j1 * (nx + 1) + i1))
    faces.append(tuple(range(base + m - 1, base - 1, -1)))
    return kit.mesh(name, verts, faces, mat=mat, parent=parent, bevel=0.012)


def _floor_wear(x, y):
    """Cart ruts at the wheel track and a dish down the middle where people walk."""
    rut = 0.022 * math.exp(-((abs(x) - 0.66) / 0.09) ** 2)
    dish = 0.026 * math.exp(-(x / 0.85) ** 2) * (0.45 + 0.55 * math.exp(-y / 1.6))
    return rut + dish


def _threshold_wear(x, y):
    """The inner threshold: dished across the middle, ruts where the wheels climb it."""
    return (0.034 * math.exp(-(x / 0.9) ** 2) * math.exp(-((y - 0.1) / 0.5) ** 2)
            + 0.018 * math.exp(-((abs(x) - 0.66) / 0.1) ** 2))


def _floor(kit, mats, rng, root):
    stone = _dressed(mats["stone_wall"])
    _slab(kit, "threshold", -HALF - 0.1, HALF + 0.1, -0.30, 0.52, 0.065, stone, root, rng, thick=0.16,
          wear=_threshold_wear, nx=12, ny=4, tilt=0.004)
    # flagstones in staggered rows to the outer face
    y = 0.52
    row = 0
    while y < PASSAGE + 0.05:
        y1 = min(y + rng.uniform(0.85, 1.2), PASSAGE + 0.1)
        cuts = [-HALF - 0.1]
        x = cuts[0] + (0.45 if row % 2 else 0.0)
        while x < HALF - 0.15:
            if x > cuts[-1]:
                cuts.append(x)
            x += rng.uniform(0.55, 1.15)
        cuts.append(HALF + 0.1)
        for k in range(len(cuts) - 1):
            if cuts[k + 1] - cuts[k] < 0.2:
                continue
            _slab(kit, f"flag_{row}_{k}", cuts[k] + 0.012, cuts[k + 1] - 0.012, y + 0.012, y1 - 0.012,
                  0.032 + kit.jitter(rng, 0.008), stone, root, rng, thick=0.1, wear=_floor_wear,
                  nx=max(2, int((cuts[k + 1] - cuts[k]) / 0.18)), ny=3, tilt=0.006)
        y = y1
        row += 1
    # mud and dirt drifted against the foot of the walls and trodden into the joints
    mud = mats["mud"]
    for side in (-1, 1):
        y = 0.6
        while y < 3.4:
            r = rng.uniform(0.16, 0.34)
            kit.sphere("mud_drift", r, (side * (HALF - 0.04 - r * 0.2), y, 0.0),
                       scale=(1.0, rng.uniform(1.2, 2.2), 0.20), mat=mud, segments=8, parent=root)
            y += rng.uniform(0.45, 0.9)
    for _ in range(5):
        kit.sphere("mud_clot", 0.2, (rng.uniform(-0.9, 0.9), rng.uniform(0.2, 1.1), 0.02),
                   scale=(rng.uniform(0.6, 1.6), rng.uniform(0.6, 1.2), 0.07), mat=mud, segments=8, parent=root)


# ---------- doors ----------

def _leaf(kit, mats, rng, root, side):
    wood, iron = mats["door_wood"], mats["iron"]
    tag = "R" if side > 0 else "L"
    y = DOOR_Y
    r = DOOR_R + 0.08   # planks tuck behind the arch stones

    # Vertical planks whose tops follow the arch.
    n = 6
    x0 = 0.01
    pw = (r - x0) / n
    for k in range(n):
        xa, xb = x0 + k * pw + 0.004, x0 + (k + 1) * pw - 0.004
        xc = (xa + xb) / 2
        top = SPRING + math.sqrt(max(r ** 2 - xc ** 2, 0.0)) + kit.jitter(rng, 0.02)
        bottom = 0.11
        face = y + abs(kit.jitter(rng, 0.02))
        kit.box(f"plank_{tag}{k}", (xb - xa, 0.10, top - bottom),
                (side * xc, face + 0.05, (top + bottom) / 2),
                mat=wood, bevel=0.012, parent=root)

    # Iron straps across the leaf, each ending in a hinge eye at the outer edge.
    for b, z in enumerate((0.55, 1.35, 2.15, 2.95)):
        length = DOOR_R - 0.02
        kit.box(f"band_{tag}{b}", (length, 0.05, 0.15),
                (side * (0.02 + length / 2), y - 0.02, z + kit.jitter(rng, 0.01)),
                mat=iron, bevel=0.01, parent=root)
        kit.cylinder(f"hinge_{tag}{b}", 0.06, 0.22, (side * (DOOR_R - 0.09), y - 0.06, z),
                     mat=iron, segments=8, bevel=0.008, parent=root)
        for s in range(5):
            kit.cylinder(f"stud_{tag}{b}_{s}", 0.034, 0.045,
                         (side * (0.15 + s * 0.22), y - 0.05, z + kit.jitter(rng, 0.006)),
                         rot_deg=(90, 0, 0), mat=iron, segments=6, parent=root)

    # Short strap in the arch, where the leaf is narrower.
    za = 3.7
    length = math.sqrt(max(DOOR_R ** 2 - (za - SPRING + 0.08) ** 2, 0.0)) - 0.04
    kit.box(f"band_{tag}4", (length, 0.05, 0.15), (side * (0.02 + length / 2), y - 0.02, za),
            mat=iron, bevel=0.01, parent=root)
    for s in range(3):
        kit.cylinder(f"stud_{tag}4_{s}", 0.034, 0.045, (side * (0.16 + s * 0.28), y - 0.05, za),
                     rot_deg=(90, 0, 0), mat=iron, segments=6, parent=root)

    # Ring handle hanging from a boss near the meeting edge.
    hx = side * 0.34
    kit.cylinder(f"boss_{tag}", 0.065, 0.045, (hx, y - 0.03, 1.65), rot_deg=(90, 0, 0),
                 mat=iron, segments=10, parent=root)
    kit.torus(f"ring_{tag}", 0.095, 0.017, (hx, y - 0.065, 1.65 - 0.09), rot_deg=(90, 0, 0),
              mat=iron, major_segments=16, minor_segments=6, parent=root)


def _bar(kit, mats, root):
    """Drawbar across both leaves in four iron keepers, its ends sunk into sockets in the jambs."""
    iron, wood = mats["iron"], mats["wood_dark"]
    y = DOOR_Y - 0.14
    z = 1.05
    kit.box("drawbar", (HALF * 2 - 0.02, 0.14, 0.14), (0, y, z), mat=wood, bevel=0.012, parent=root)
    for i, x in enumerate((-0.95, -0.32, 0.32, 0.95)):
        kit.box(f"keeper_{i}_top", (0.08, 0.20, 0.025), (x, y, z + 0.082), mat=iron, bevel=0.004, parent=root)
        kit.box(f"keeper_{i}_leg", (0.08, 0.025, 0.2), (x, y - 0.085, z), mat=iron, bevel=0.004, parent=root)


# ---------- portcullis, vault fittings ----------

BAR = 0.06            # portcullis bar section
CELL = (0.29, 0.42)   # lattice spacing, x and z
TIP = 3.42            # lowest spike tip of the raised portcullis
SLOT_TOP = 6.2        # grille runs up into the slot to this height


def _vault_z(x):
    """Height of the vault soffit at x."""
    return SPRING + math.sqrt(max(HALF ** 2 - x ** 2, 0.0))


def _portcullis(kit, mats, rng, root):
    iron = mats["iron"]
    foot = TIP + 0.16
    n = int((2 * 1.46) / CELL[0]) + 1
    xs = [-1.46 + i * (2 * 1.46) / (n - 1) for i in range(n)]
    for i, x in enumerate(xs):
        lag = rng.uniform(-0.05, 0.05) if 0 < i < n - 1 else 0.0   # a few bars hang a little lower
        f = foot + lag
        kit.box(f"pc_bar_{i}", (BAR, BAR, SLOT_TOP - f), (x, SLOT_Y, (SLOT_TOP + f) / 2),
                rot_deg=(0, kit.jitter(rng, 0.3), 0), mat=iron, bevel=0.006, parent=root)
        kit.cylinder(f"pc_spike_{i}", BAR * 0.62, 0.20, (x, SLOT_Y, f - 0.09),
                     rot_deg=(180, 0, 0), mat=iron, segments=4, radius_top=0.0, parent=root)
    z = foot + 0.22
    k = 0
    while z < SLOT_TOP - 0.1:
        kit.box(f"pc_rail_{k}", (2 * 1.50, BAR * 0.9, BAR),
                (0, SLOT_Y + (BAR * 0.7 if k % 2 else -BAR * 0.7), z), mat=iron, bevel=0.006, parent=root)
        z += CELL[1] + kit.jitter(rng, 0.01)
        k += 1
    # the heavy bottom rail the spikes are forged to
    kit.box("pc_shoe", (2 * 1.50, BAR * 1.6, BAR * 1.3), (0, SLOT_Y, foot + 0.04), mat=iron, bevel=0.008,
            parent=root)
    # guide runners in the grooves
    for side in (-1, 1):
        kit.box(f"pc_guide_{side}", (0.07, 0.1, SLOT_TOP - foot), (side * 1.55, SLOT_Y, (SLOT_TOP + foot) / 2),
                mat=iron, bevel=0.01, parent=root)


def _hole_frames(kit, mats, root):
    """Dressed square collars around the murder holes, tilted to lie on the vault."""
    stone = _dressed(mats["stone_wall"])
    for side in (-1, 1):
        x = side * HOLE_X
        phi = math.degrees(math.asin(HOLE_X / HALF))
        grp = kit.group(f"hole_frame_{side}", (x, HOLE_Y, _vault_z(x) - 0.02), parent=root)
        grp.rotation_euler = (0, math.radians(side * phi), 0)
        outer, t = 0.58, 0.07
        strip = (outer - HOLE) / 2
        c = (HOLE + strip) / 2
        for name, size, loc in (("a", (outer, strip, t), (0, c)), ("b", (outer, strip, t), (0, -c)),
                                ("c", (strip, HOLE, t), (c, 0)), ("d", (strip, HOLE, t), (-c, 0))):
            kit.box(f"hole_{side}_{name}", size, (loc[0], loc[1], -t / 2), mat=stone, bevel=0.01, parent=grp)


def _torch(kit, mats, rng, root):
    """Burning torch in an iron sconce on the east side wall, a soot streak above it, and its light."""
    from . import _lights, _soot, torch_sconce

    grp = kit.group("passage_torch", (HALF, TORCH_Y, TORCH_Z), parent=root)
    grp.rotation_euler = (0, 0, math.radians(-90))     # sconce back (+Y) to the wall, torch out toward -X
    grp.scale = (TORCH_SCALE,) * 3
    torch_sconce.bracket(kit, mats, grp)
    torch_sconce.burning_torch(kit, mats, rng, grp)
    spec = dict(torch_sconce.TORCH_LIGHT, watts=TORCH_WATTS, reach=6.0)
    _lights.add(grp, "passage_torch", **spec).data.volume_factor = torch_sconce.VOLUME_FACTOR
    _lights.add(root, "passage_fill", (0.0, 1.20, 1.10), (1.0, 0.40, 0.10), 14.0, radius=0.4, specular=0.2,
                reach=4.0)
    # soot: from just over the flame up the wall to the springing of the vault
    _soot.plume(kit, grp, "passage_soot", (0.0, -0.004, 0.30), 0.55, (SPRING + 0.1 - TORCH_Z) / TORCH_SCALE - 0.30,
                strength=0.95)


# ---------- cut ----------

def _cut_passage(kit, root):
    """Cut the passage through the gatehouse, plus the portcullis slot and the murder holes."""
    blocks = [b for b in (bpy.data.objects.get(n) for n in CUT_BLOCKS) if b is not None]
    if not blocks:
        return
    e = 0.004                                   # a hair bigger than the cut build_scene.py makes
    y0, y1 = 0.5, PASSAGE + 0.25
    ym = (y0 + y1) / 2
    cutters = [
        kit.box("cut_gate_passage", (2 * HALF + 2 * e, y1 - y0, SPRING + 0.2), (0, ym, SPRING / 2 - 0.1),
                parent=root),
        kit.cylinder("cut_gate_vault", HALF + e, y1 - y0, (0, ym, SPRING), (90, 0, 0), segments=32, parent=root),
        # slot and grooves: from the floor, up past the crown, into the room above
        kit.box("cut_gate_slot", (2 * HALF + 0.24, SLOT_W, 6.6), (0, SLOT_Y, 3.1), parent=root),
    ]
    for side in (-1, 1):
        cutters.append(kit.box(f"cut_gate_hole_{side}", (HOLE, HOLE, 2.4), (side * HOLE_X, HOLE_Y, 5.3),
                               parent=root))
    for c in cutters:
        c.hide_render = True
        c.display_type = "WIRE"
        for block in blocks:
            mod = block.modifiers.new(c.name, "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.object = c


def build(kit, mats, rng):
    root = kit.group("gate_door")
    _cut_passage(kit, root)
    _portal(kit, mats, rng, root, "inner", -FRONT, BACK)
    outer = kit.group("outer_portal", (0, PASSAGE, 0), parent=root)
    outer.rotation_euler = (0, 0, math.pi)
    _portal(kit, mats, rng, outer, "outer", -FRONT, BACK)
    _floor(kit, mats, rng, root)
    _door_arch(kit, mats, rng, root)
    for side in (-1, 1):
        _leaf(kit, mats, rng, root, side)
    kit.box("seam_strip", (0.07, 0.04, 4.0), (0, DOOR_Y - 0.03, 0.11 + 4.0 / 2),
            mat=mats["iron"], bevel=0.008, parent=root)
    _bar(kit, mats, root)
    _portcullis(kit, mats, rng, root)
    _hole_frames(kit, mats, root)
    _torch(kit, mats, rng, root)
    return root
