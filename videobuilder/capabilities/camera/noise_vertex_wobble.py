"""Noise Vertex Wobble: every vertex of a 3D mesh is pushed in or out along
its normal by smooth noise that flows over time, so the solid's surface
heaves and ripples like soft matter while it turns.

`icosphere` builds the mesh, `noise_wobble` displaces it for a moment `t`,
and `draw_mesh` projects, lights and paints it flat-shaded with a painter's
sort, so a film can wobble any closed mesh it has.
"""
import math
from functools import lru_cache

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def _hash(i, j, k, seed):
    """A deterministic value in [-1, 1] for lattice point (i, j, k)."""
    h = (i * 374761393 + j * 668265263 + k * 1440662683 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 32767.5 - 1.0


def noise3(x, y, z, seed=0):
    """Smooth 3-D value noise in [-1, 1]."""
    i, j, k = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - i, y - j, z - k
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def lerp(a, b, f):
        return a + (b - a) * f

    def edge(dj, dk):
        return lerp(_hash(i, j + dj, k + dk, seed), _hash(i + 1, j + dj, k + dk, seed), fx)
    return lerp(lerp(edge(0, 0), edge(1, 0), fy), lerp(edge(0, 1), edge(1, 1), fy), fz)


def icosphere(level=3):
    """A unit sphere as (vertices, faces): an icosahedron split `level`
    times, vertices as (x, y, z) on the sphere, faces as index triples wound
    counter-clockwise seen from outside."""
    g = (1 + 5 ** 0.5) / 2
    verts = [(-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0), (0, -1, g), (0, 1, g), (0, -1, -g),
             (0, 1, -g), (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1)]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
             (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]

    def unit(v):
        d = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        return (v[0] / d, v[1] / d, v[2] / d)
    verts = [unit(v) for v in verts]
    for _ in range(level):
        mids = {}

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in mids:
                va, vb_ = verts[a], verts[b]
                verts.append(unit(((va[0] + vb_[0]) / 2, (va[1] + vb_[1]) / 2, (va[2] + vb_[2]) / 2)))
                mids[key] = len(verts) - 1
            return mids[key]
        out = []
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = out
    return verts, faces


def noise_wobble(vertices, normals, t, amount=0.18, size=0.9, speed=0.6, octaves=2, seed=0):
    """`vertices` at time `t` (seconds), each pushed along its normal by
    smooth 3-D noise sampled at its rest position, so redrawing every frame
    with a rising `t` makes the surface undulate. `amount`: the largest push,
    in the mesh's units. `size`: the noise's feature size in those units
    (smaller gives more, tighter lumps). `speed`: how fast the lumps flow.
    `octaves`: layers of finer detail. Deterministic for a given `seed` and
    `t`; `amount=0` returns the vertices unchanged."""
    drift = t * speed
    out = []
    for (x, y, z), (nx, ny, nz) in zip(vertices, normals):
        u, v, w = x / size, y / size, z / size
        push, amp, norm = 0.0, 1.0, 0.0
        for o in range(octaves):
            f = 2 ** o
            push += amp * noise3(u * f + drift, v * f - 0.7 * drift, w * f + 0.4 * drift, seed + o)
            norm += amp
            amp *= 0.5
        push = amount * push / norm
        out.append((x + nx * push, y + ny * push, z + nz * push))
    return out


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def draw_mesh(cv, vertices, faces, cx, cy, radius, color, yaw=0.0, pitch=0.0, light=(-0.5, -0.7, -0.6),
              distance=6.0, ambient=0.28):
    """Paint a closed mesh flat-shaded, centred at (cx, cy) with one mesh
    unit drawn `radius` px across. It is turned `yaw` then `pitch` radians
    and seen in perspective from `distance` units; back faces are dropped
    and the rest painted far to near, each lit by `light` (a direction
    towards the light: screen x right, y down, z into the frame) over an
    `ambient` floor. Returns the drawn Box."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    world = []
    for x, y, z in vertices:
        x, z = x * cy_ + z * sy_, -x * sy_ + z * cy_
        y, z = y * cp - z * sp, y * sp + z * cp
        world.append((x, -y, z))   # mesh y is up; the canvas's is down
    screen = [(cx + x * radius * distance / (distance + z), cy + y * radius * distance / (distance + z))
              for x, y, z in world]
    ld = math.sqrt(sum(c * c for c in light))
    lx, ly, lz = (c / ld for c in light)
    r, g, b, _ = rgba(color)
    drawn = []
    for f in faces:
        a, b_, c = (world[i] for i in f)
        nx, ny, nz = _cross(_sub(c, a), _sub(b_, a))   # the y flip mirrors the winding
        d = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / d, ny / d, nz / d
        centre = ((a[0] + b_[0] + c[0]) / 3, (a[1] + b_[1] + c[1]) / 3, (a[2] + b_[2] + c[2]) / 3 + distance)
        if nx * centre[0] + ny * centre[1] + nz * centre[2] >= 0:
            continue   # facing away from the camera
        k = ambient + (1 - ambient) * max(0.0, nx * lx + ny * ly + nz * lz)
        drawn.append((centre[2], f, k))
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_width(0.8)
    ctx.set_line_join(1)   # round, so the seam-hiding stroke never spikes
    for _, f, k in sorted(drawn, key=lambda d: -d[0]):
        ctx.move_to(*screen[f[0]])
        ctx.line_to(*screen[f[1]])
        ctx.line_to(*screen[f[2]])
        ctx.close_path()
        ctx.set_source_rgb(r * k, g * k, b * k)
        ctx.fill_preserve()
        ctx.stroke()
    ctx.restore()
    xs, ys = [p[0] for p in screen], [p[1] for p in screen]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@lru_cache(maxsize=None)
def _sphere():
    return icosphere(4)


def draw(n, cv):
    t = n / demo.FPS
    verts, faces = _sphere()
    cx, cy, radius = demo.W / 2, demo.H / 2 - 20, 150
    # A soft contact shadow, so the blob floats over a floor.
    with cv.layer(opacity=0.5):
        cv.shape_shadow([(cx + 120 * math.cos(a), cy + 205 + 14 * math.sin(a))
                         for a in (i * math.pi / 24 for i in range(48))], blur=16, color=(0, 0, 0, 0.9))
    wobbled = noise_wobble(verts, verts, t, amount=0.28, size=0.7, speed=1.1, octaves=1, seed=5)
    box = draw_mesh(cv, wobbled, faces, cx, cy, radius, '#a9b0ee', yaw=0.5 * t, pitch=0.35)
    cv.mark('mesh', *box)


CAPABILITY = Capability(
    id='noise-vertex-wobble',
    name='Noise vertex wobble',
    family='camera',
    group='3D motion',
    aliases=('organic noise deform', 'simplex blob', 'noise displacement', 'vertex noise'),
    definition='A 3D shape keeps bulging and sinking all over as its surface points are nudged in and '
               'out by smoothly changing noise, so it looks soft and alive.',
    phrasings=('make the sphere squish and bulge like a lump of jelly',
               'a 3D blob whose surface keeps rippling organically while it spins',
               'deform the mesh with moving noise so it breathes'),
    related=('domain-warping', 'wiggle-path', 'wobble', 'noise-field-warp', 'worley-cellular-noise',
             'fractal-brownian-motion'),
    api=('videobuilder.capabilities.camera.noise_vertex_wobble.noise_wobble',
         'videobuilder.capabilities.camera.noise_vertex_wobble.icosphere',
         'videobuilder.capabilities.camera.noise_vertex_wobble.draw_mesh',
         'videobuilder.capabilities.camera.noise_vertex_wobble.noise3'),
    demo=lambda: demo.film(draw),
)
