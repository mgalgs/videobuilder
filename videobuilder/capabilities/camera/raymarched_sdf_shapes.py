"""Raymarched SDF shapes: 3D solids described only by signed distance
functions, rendered per pixel by sphere tracing -- each ray steps forward by
the distance to the nearest surface until it lands on one -- then lit with
normals taken from the field itself. Because the shapes are just numbers,
they blend into one another with a smooth union and melt like wax.

Needs numpy (imported when a frame is drawn, so the registry loads without it).
"""
import math

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


# Distance primitives. `p` is a point (x, y, z) of numpy arrays; each returns
# the signed distance from `p` to the surface (negative inside).

def sdf_sphere(p, r):
    """A sphere of radius `r` at the origin."""
    np = _np()
    x, y, z = p
    return np.sqrt(x * x + y * y + z * z) - r


def sdf_box(p, half, rounding=0.0):
    """A box with half-extents `half` (hx, hy, hz), edges rounded by `rounding`."""
    np = _np()
    q = [np.abs(c) - (h - rounding) for c, h in zip(p, half)]
    outside = np.sqrt(sum(np.maximum(c, 0) ** 2 for c in q))
    inside = np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)
    return outside + inside - rounding


def sdf_torus(p, major, minor):
    """A ring lying in the xz plane: `major` radius to the tube's centre, `minor` tube radius."""
    np = _np()
    x, y, z = p
    return np.sqrt((np.sqrt(x * x + z * z) - major) ** 2 + y * y) - minor


def smooth_union(d1, d2, k):
    """The two fields joined with a rounded fillet of size `k` instead of a crease."""
    np = _np()
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0, 1)
    return d2 + (d1 - d2) * h - k * h * (1 - h)


def translate(p, offset):
    """`p` moved into the frame of a shape placed at `offset`."""
    return tuple(c - o for c, o in zip(p, offset))


def rotate(p, yaw=0.0, pitch=0.0):
    """`p` turned into the frame of a shape rotated by `yaw` (about y) then `pitch` (about x)."""
    x, y, z = p
    c, s = math.cos(-yaw), math.sin(-yaw)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(-pitch), math.sin(-pitch)
    y, z = c * y - s * z, s * y + c * z
    return x, y, z


def _np():
    import numpy
    return numpy


def _hex(color):
    return vb.rgba(color)[:3]


def render_sdf(scene, width, height, eye=(0.0, 1.2, -6.0), target=(0.0, 0.0, 0.0), fov=40.0,
               light=(-0.5, 0.8, -0.6), color=None, background=demo.BG, floor=-1.0,
               floor_color='#2a2c33', steps=40, far=30.0):
    """Raymarch `scene` to a `width` x `height` PIL image.

    `scene(p)` returns signed distances for points `p` = (x, y, z) arrays,
    built from `sdf_sphere`, `sdf_box`, `sdf_torus`, `smooth_union`,
    `translate` and `rotate` (or any numpy maths). `color(p)` returns an
    (r, g, b) of 0-1 arrays for the surface at `p`, defaulting to the kit's
    accent. Rays leave `eye` towards `target` over a vertical `fov` in
    degrees; `light` is the direction towards the sun. A ground plane at
    y = `floor` catches soft shadows (None for no floor); misses fade to
    `background`."""
    np = _np()
    aspect = width / height
    eye = np.array(eye, float)
    fwd = np.array(target, float) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross((0.0, 1.0, 0.0), fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    f = math.tan(math.radians(fov) / 2)
    u = (np.arange(width) + 0.5) / width * 2 - 1
    v = 1 - (np.arange(height) + 0.5) / height * 2
    U, V = np.meshgrid(u * f * aspect, v * f)
    U, V = U.ravel(), V.ravel()
    rd = [fwd[i] + U * right[i] + V * up[i] for i in range(3)]
    norm = np.sqrt(sum(c * c for c in rd))
    rd = [c / norm for c in rd]
    n = U.size
    sun = np.array(light, float)
    sun /= np.linalg.norm(sun)

    # Sphere trace: each live ray steps by the scene's distance at its tip.
    t = np.zeros(n)
    hit = np.zeros(n, bool)
    live = np.arange(n)
    for _ in range(steps):
        if live.size == 0:
            break
        tl = t[live]
        p = tuple(eye[i] + rd[i][live] * tl for i in range(3))
        d = scene(p)
        t[live] = tl + d
        landed = d < 0.0015 * tl + 0.0005
        hit[live[landed]] = True
        live = live[~landed & (t[live] < far)]

    bg = np.array(_hex(background))
    out = np.tile(bg, (n, 1))

    def shadow(idx, origin):
        # Soft shadow: how close a ray towards the sun passes to any surface.
        res = np.ones(idx.size)
        s = np.full(idx.size, 0.05)
        for _ in range(14):
            p = tuple(origin[i] + sun[i] * s for i in range(3))
            d = scene(p)
            res = np.minimum(res, 8 * d / s)
            s = s + np.clip(d, 0.02, 0.4)
        return np.clip(res, 0, 1) ** 1.5

    # Floor: rays that missed (or passed behind) the shapes and meet the plane.
    if floor is not None:
        with np.errstate(divide='ignore', invalid='ignore'):
            tf = (floor - eye[1]) / rd[1]
        fl = np.nonzero((tf > 0) & (~hit | (tf < t)))[0]
        if fl.size:
            tfl = tf[fl]
            p = [eye[i] + rd[i][fl] * tfl for i in range(3)]
            sh = shadow(fl, p)
            fc = np.array(_hex(floor_color))
            lit = (0.55 + 0.45 * sh)[:, None] * fc * (0.6 + 0.6 * max(sun[1], 0))
            fog = np.clip((tfl - 4) / 14, 0, 1)[:, None]
            out[fl] = lit * (1 - fog) + bg * fog
            hit[fl] = False

    idx = np.nonzero(hit)[0]
    if idx.size:
        th = t[idx]
        p = [eye[i] + rd[i][idx] * th for i in range(3)]
        # Normal: the field's gradient, from a tetrahedron of four samples.
        e = 0.0015
        nrm = [np.zeros(idx.size) for _ in range(3)]
        for k in ((1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, 1, 1)):
            d = scene(tuple(p[i] + k[i] * e for i in range(3)))
            for i in range(3):
                nrm[i] += k[i] * d
        ln = np.sqrt(sum(c * c for c in nrm)) + 1e-9
        nrm = [c / ln for c in nrm]
        # Ambient occlusion: how much nearby surface crowds in along the normal.
        occ = np.zeros(idx.size)
        for j in range(1, 4):
            h = 0.06 * j
            d = scene(tuple(p[i] + nrm[i] * h for i in range(3)))
            occ += (h - d) / (2 ** j)
        ao = np.clip(1 - 3 * occ, 0, 1)
        lift = [p[i] + nrm[i] * 0.01 for i in range(3)]
        sh = shadow(idx, lift)
        diff = np.clip(sum(nrm[i] * sun[i] for i in range(3)), 0, 1) * sh
        view = [-rd[i][idx] for i in range(3)]
        half = [sun[i] + view[i] for i in range(3)]
        hl = np.sqrt(sum(c * c for c in half)) + 1e-9
        spec = np.clip(sum(nrm[i] * half[i] / hl for i in range(3)), 0, 1) ** 48 * sh
        sky = 0.5 + 0.5 * nrm[1]
        rim = (1 - np.clip(sum(nrm[i] * view[i] for i in range(3)), 0, 1)) ** 3
        if color is None:
            base = np.tile(np.array(_hex(demo.ACCENT)), (idx.size, 1))
        else:
            base = np.stack([np.broadcast_to(c, (idx.size,)) for c in color(tuple(p))], axis=1)
        light_ = (1.05 * diff + 0.28 * sky * ao)[:, None]
        rgb = base * light_ + (0.9 * spec + 0.25 * rim * ao)[:, None]
        out[idx] = rgb

    out = np.clip(out, 0, 1) ** (1 / 1.1)
    pixels = (out.reshape(height, width, 3) * 255 + 0.5).astype(np.uint8)
    return PILImage.fromarray(pixels, 'RGB')


def draw_sdf(cv, scene, x, y, w, h, max_res=420, **kw):
    """Raymarch `scene` into the box (x, y, w, h) of `cv`. It renders at the
    box's on-screen pixel size, capped at `max_res` wide, and is stretched
    to fit; `kw` passes to `render_sdf` (camera, light, colour, floor)."""
    px = max(8, min(max_res, round(w * cv.scale_factor())))
    py = max(8, round(px * h / w))
    cv.image(vb.Image.from_pil(render_sdf(scene, px, py, **kw)), x, y, w, h)


# The demo: a sphere, a rounded box and a ring that slide together, melt
# into one blob through a smooth union, and pull apart again, while the
# camera drifts round them.

_PALETTE = (demo.ACCENT, demo.TEAL, '#f2c14e')


def _shapes(p, time):
    np = _np()
    spread = 0.3 + 0.7 * (0.5 + 0.5 * math.cos(2 * math.pi * time / demo.SECONDS))
    bob = 0.12 * math.sin(2 * math.pi * time / demo.SECONDS)
    a = sdf_sphere(translate(p, (-1.7 * spread, bob, 0)), 0.8)
    b = sdf_box(rotate(translate(p, (0, -bob, 0)), yaw=1.2 * time, pitch=0.6 * time),
                (0.62, 0.62, 0.62), rounding=0.12)
    c = sdf_torus(rotate(translate(p, (1.7 * spread, bob, 0)), yaw=0.4, pitch=1.3 + 1.1 * time), 0.62, 0.22)
    return np.stack([a, b, c])


def demo_scene(time):
    """The demo's (scene, color) pair at `time` seconds."""
    np = _np()
    cols = np.array([_hex(c) for c in _PALETTE])

    def scene(p):
        a, b, c = _shapes(p, time)
        return smooth_union(smooth_union(a, b, 0.45), c, 0.45)

    def color(p):
        d = _shapes(p, time)
        wts = np.exp(-np.maximum(d, 0) * 9)  # nearest shape dominates; blends in the fillets
        wts /= wts.sum(axis=0)
        return tuple((cols[:, i, None] * wts).sum(axis=0) for i in range(3))

    return scene, color


def _demo_draw(n, cv):
    time = n / demo.FPS
    scene, color = demo_scene(time)
    orbit = 0.35 * math.sin(2 * math.pi * time / demo.SECONDS) - 0.25
    eye = (5.5 * math.sin(orbit), 1.6, -5.5 * math.cos(orbit))
    draw_sdf(cv, scene, 0, 0, demo.W, demo.H, eye=eye, target=(0, -0.2, 0), fov=36,
             color=color, floor=-0.95)


CAPABILITY = Capability(
    id='raymarched-sdf-shapes',
    name='Raymarched SDF shapes',
    family='camera',
    group='Shader looks',
    aliases=('sphere tracing', 'signed distance field rendering', 'SDF raymarching', 'smooth union blobs'),
    definition='Glossy 3D solids are drawn from distance formulas, pixel by pixel, so they can glide into '
               'each other and fuse like soft wax before pulling apart again.',
    phrasings=('render some 3D shapes with a shader so they melt together',
               'a sphere and a cube that blob into each other like liquid',
               'that raymarching demo look with smooth shaded shapes'),
    related=('mandelbulb-raymarch', 'god-rays', 'diffraction-spikes', 'marching-squares-contour',
             'graphic-match', 'depth-of-field'),
    api=('videobuilder.capabilities.camera.raymarched_sdf_shapes.draw_sdf',
         'videobuilder.capabilities.camera.raymarched_sdf_shapes.render_sdf',
         'videobuilder.capabilities.camera.raymarched_sdf_shapes.sdf_sphere',
         'videobuilder.capabilities.camera.raymarched_sdf_shapes.sdf_box',
         'videobuilder.capabilities.camera.raymarched_sdf_shapes.sdf_torus',
         'videobuilder.capabilities.camera.raymarched_sdf_shapes.smooth_union'),
    demo=lambda: demo.film(_demo_draw),
)
