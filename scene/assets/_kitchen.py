"""Building pieces shared by the cookhouse props: vessels turned on a lathe, flat blobs, a coal material.

Not a prop module: the leading underscore keeps it out of assets.available().
"""

import math

from . import _shed_geo as geo
from . import _shed_props as props


def lathe(kit, name, profile, segments, mat, loc=(0.0, 0.0, 0.0), parent=None, smooth=True, bevel=0.0):
    """A surface of revolution about the local Z axis through the (radius, height) points of `profile`,
    in order. A radius of 0 closes the surface in one point."""
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r <= 1e-6:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1] * segments)
        else:
            base = len(verts)
            verts += [(r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z)
                      for i in range(segments)]
            rings.append(list(range(base, base + segments)))
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            quad = (a[i], a[j], b[j], b[i])
            quad = tuple(dict.fromkeys(quad))          # a ring collapsed into its centre makes triangles
            if len(quad) >= 3:
                faces.append(quad)
    ob = kit.mesh(name, verts, faces, loc, mat=mat, parent=parent, bevel=bevel)
    for p in ob.data.polygons:
        p.use_smooth = smooth
    return ob


def blob(kit, name, loc, radii, mat, parent, rot_z=0.0, segments=10):
    """A flattened ellipsoid: a heap of flour, a puddle of ash, a loaf, an onion."""
    return kit.sphere(name, 1.0, loc, scale=radii, rot_deg=(0, 0, rot_z), mat=mat, segments=segments, parent=parent)


def scatter_blobs(kit, rng, name, mat, parent, centre, spread, n, size, height, z=0.0, region=None):
    """`n` small flat blobs around `centre`, one merged object; `region(x, y)` can reject a point."""
    m = geo.Mesh()
    tries = 0
    while n > 0 and tries < n * 20:
        tries += 1
        x, y = rng.gauss(centre[0], spread[0]), rng.gauss(centre[1], spread[1])
        if region and not region(x, y):
            continue
        s = rng.uniform(*size)
        m.ellipsoid((x, y, z + height * 0.3), (s, s * rng.uniform(0.6, 1.3), height), (0, 0, rng.uniform(0, 180)), segments=8)
        n -= 1
    return m.finish(name, mat, parent)


# (height fraction, radius factor) of a grain sack sewn shut across the top, from foot to closure
SACK_PROFILE = ((0.0, 0.0), (0.04, 0.95), (0.12, 1.0), (0.4, 1.03), (0.7, 0.97), (0.86, 0.9), (0.95, 0.78),
                (0.99, 0.5), (1.0, 0.0))


def sack(kit, rng, name, mat, parent, loc, height=0.7, radius=0.25, rot=(0.0, 0.0, 0.0), flat=0.82):
    """A slumped, lumpy grain sack: a lathe shape squashed a little, every vertex nudged."""
    profile = [(radius * rf, height * hf) for hf, rf in SACK_PROFILE]
    ob = lathe(kit, name, profile, 16, mat, loc, parent, smooth=True)
    me = ob.data
    for v in me.vertices:
        v.co.y *= flat
        k = 1.0 + rng.uniform(-0.05, 0.05)
        v.co.x, v.co.y = v.co.x * k, v.co.y * k
        v.co.z += rng.uniform(-0.012, 0.012)
    ob.rotation_euler = [math.radians(a) for a in rot]
    return ob


def coal_material(mats):
    """The coals material under the name anim.py recognises as embers."""
    m = mats["coals"]
    if not m.name.startswith("embers"):
        m.name = "embers.coals"
    return m


class Provisions(props.Provisions):
    """The shed's hung provisions, with hams and sausages smoked brown (the shed's are red cloth)."""

    def finish(self, mats, root):
        self.rope.finish("prov_cord", mats["rope"], root)
        self.meat.finish("prov_meat", mats["clay"], root, smooth=True)
        self.herb.finish("prov_herbs", mats["moss"], root)
        self.onion.finish("prov_onions", mats["straw"], root, smooth=True)
        self.iron.finish("prov_hooks", mats["iron"], root)
