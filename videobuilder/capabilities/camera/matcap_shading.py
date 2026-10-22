"""Matcap Shading: the whole lighting of a surface comes from one picture of
a lit ball (the matcap). Each visible point looks up the colour of the ball
where the ball's normal faces the same way as its own, so the shine stays
put on screen while the form turns underneath it."""
import math

import numpy as np
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def _rgb(color):
    return np.array(vb.rgba(color)[:3])


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) or 1.0)


def make_matcap(size=256, base='#7d86e0', shadow='#1c1f4a', rim='#b9c2ff', band='#ffc21a',
                highlight='#ffffff', light=(-0.45, -0.55, 0.7), band_at=0.22, band_width=0.09):
    """A matcap: a `size` x `size` float RGB array (0 -> 1) of a lit ball,
    axes x right, y down, the ball filling the square. `base` lit by `light`
    (x right, y down, z towards the viewer) fades to `shadow`, the edge picks
    up a soft `rim`, a glossy `band` stripe runs across it at height
    `band_at` (-1 top, 1 bottom; `band=None` for none) and a hard white
    `highlight` sits towards the light. Pixels outside the ball repeat its
    edge, so any normal looks up a sensible colour."""
    s = (np.arange(size) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(s, s)
    r = np.hypot(x, y)
    k = np.where(r > 0.999, 0.999 / np.maximum(r, 1e-9), 1.0)   # pull outside pixels onto the rim
    x, y = x * k, y * k
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    n = np.stack([x, y, z], axis=-1)
    lv = _unit(light)
    d = np.clip(n @ lv, 0, 1)[..., None]
    out = _rgb(shadow) + (_rgb(base) - _rgb(shadow)) * d ** 0.8
    fres = ((1 - z) ** 3)[..., None]
    out = out + (_rgb(rim) - out) * fres * 0.7
    if band is not None:
        b = np.exp(-((y - band_at + 0.15 * x * x) / band_width) ** 2)[..., None]
        out = out + (_rgb(band) - out) * b * (0.35 + 0.65 * d)
    hv = _unit(lv + np.array([0.0, 0.0, 1.0]))
    spec = (np.clip(n @ hv, 0, 1) ** 90)[..., None]
    out = out + (_rgb(highlight) - out) * np.clip(spec * 1.4, 0, 1)
    return np.clip(out, 0, 1)


def matcap_lookup(matcap, nx, ny):
    """The matcap colour for view-space normals (`nx`, `ny` arrays, x right,
    y down, each -1 -> 1): float RGB, one per normal. The normal must be in
    view space -- after the object's rotation -- or the light turns with it."""
    size = matcap.shape[0]
    u = np.clip(((nx + 1) * 0.5 * size).astype(int), 0, size - 1)
    v = np.clip(((ny + 1) * 0.5 * size).astype(int), 0, size - 1)
    return matcap[v, u]


def rotation(yaw, pitch, roll=0.0):
    """A 3x3 rotation: `roll` about z, then `pitch` about x, then `yaw` about y (radians)."""
    cy, sy, cp, sp, cr, sr = (math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch),
                              math.cos(roll), math.sin(roll))
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return ry @ rx @ rz


def torus_knot(p=2, q=3, tube=0.42, along=1200, around=96):
    """Points and unit normals of a tube round a (`p`, `q`) torus knot, as two
    (N, 3) arrays, fitting within about +-3.5 units. `along` and `around`
    are the samples along the knot and round the tube."""
    t = np.linspace(0, 2 * np.pi, along, endpoint=False)
    rr = 2 + np.cos(q * t)
    c = np.stack([rr * np.cos(p * t), rr * np.sin(p * t), -np.sin(q * t)], axis=-1)
    dr = -q * np.sin(q * t)
    tan = np.stack([dr * np.cos(p * t) - p * rr * np.sin(p * t),
                    dr * np.sin(p * t) + p * rr * np.cos(p * t), -q * np.cos(q * t)], axis=-1)
    tan /= np.linalg.norm(tan, axis=-1, keepdims=True)
    radial = np.stack([np.cos(p * t), np.sin(p * t), np.zeros_like(t)], axis=-1)  # never along the tangent
    nrm = radial - (radial * tan).sum(-1, keepdims=True) * tan
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    bin_ = np.cross(tan, nrm)
    v = np.linspace(0, 2 * np.pi, around, endpoint=False)
    normals = (np.cos(v)[None, :, None] * nrm[:, None, :] + np.sin(v)[None, :, None] * bin_[:, None, :])
    points = c[:, None, :] + tube * normals
    return points.reshape(-1, 3), normals.reshape(-1, 3)


def matcap_render(points, normals, rot, matcap, px, extent=3.6):
    """Render a point-sampled surface (`points`, `normals`: (N, 3) model
    space) turned by the 3x3 `rot`, shaded by `matcap`, orthographic, into a
    `px` x `px` RGBA PIL image covering -`extent` -> `extent` on both axes.
    Sample the surface finer than a pixel or it shows holes."""
    pv = points @ rot.T
    nv = normals @ rot.T
    vis = nv[:, 2] > -0.05                      # back faces never win the depth test
    pv, nv = pv[vis], nv[vis]
    ix = ((pv[:, 0] / extent + 1) * 0.5 * px).astype(int)
    iy = ((pv[:, 1] / extent + 1) * 0.5 * px).astype(int)
    ok = (ix >= 0) & (ix < px) & (iy >= 0) & (iy < px)
    ix, iy, z, nv = ix[ok], iy[ok], pv[ok, 2], nv[ok]
    cell = iy * px + ix
    order = np.lexsort((-z, cell))              # per pixel, the nearest point (largest z) first
    cell, nv = cell[order], nv[order]
    first = np.ones(len(cell), dtype=bool)
    first[1:] = cell[1:] != cell[:-1]
    cell, nv = cell[first], nv[first]
    img = np.zeros((px * px, 4), dtype=np.uint8)
    img[cell, :3] = (matcap_lookup(matcap, nv[:, 0], nv[:, 1]) * 255 + 0.5).astype(np.uint8)
    img[cell, 3] = 255
    return PILImage.fromarray(img.reshape(px, px, 4), 'RGBA')


def draw_matcap_knot(cv, cx, cy, size, rot, matcap, p=2, q=3):
    """Draw a matcap-shaded (`p`, `q`) torus knot turned by `rot` (see
    `rotation`) in the `size` square centred at (cx, cy). Rendered at the
    canvas's real pixel size, a little over for smooth edges."""
    px = max(24, min(1400, round(size * cv.scale_factor() * 1.5)))
    extent = 3.6
    unit = px / (2 * extent)                    # pixels per model unit
    along = int(34 * unit * 1.7)                # the knot runs about 34 units around
    around = int(2 * math.pi * 0.42 * unit * 1.7) + 12
    points, normals = _knot(p, q, along, around)
    pil = matcap_render(points, normals, rot, matcap, px, extent)
    cv.image(vb.Image.from_pil(pil), cx - size / 2, cy - size / 2, size, size)
    cv.mark('matcap', cx - size / 2, cy - size / 2, size, size)


_KNOTS = {}


def _knot(p, q, along, around):
    key = (p, q, along, around)
    if key not in _KNOTS:
        _KNOTS.clear()
        _KNOTS[key] = torus_knot(p, q, along=along, around=around)
    return _KNOTS[key]


_MATCAP = []


def _demo_matcap():
    if not _MATCAP:
        _MATCAP.append(make_matcap(256))
    return _MATCAP[0]


def _ball(cv, matcap, cx, cy, r):
    """The matcap itself, shown as a small ball with a caption."""
    px = max(8, round(2 * r * cv.scale_factor() * 1.5))
    s = (np.arange(px) + 0.5) / px * 2 - 1
    x, y = np.meshgrid(s, s)
    rgb = matcap_lookup(matcap, x, y)
    a = np.clip((1 - np.hypot(x, y)) * px / 2, 0, 1)
    arr = np.concatenate([rgb, a[..., None]], axis=-1)
    cv.image(vb.Image.from_pil(PILImage.fromarray((arr * 255 + 0.5).astype(np.uint8), 'RGBA')),
             cx - r, cy - r, 2 * r, 2 * r)
    cv.arc(cx, cy, r + 2, 0, 2 * math.pi, kit.LINE, width=1.5)
    f = demo.mono(14)
    w, h = vb.text.block_size(['matcap'], f)
    vb.text.draw(cv, ['matcap'], f, cx - w / 2, cy + r + 9, demo.MUTED)


def draw(n, cv):
    t = n / demo.FPS / demo.SECONDS
    rot = rotation(2 * math.pi * t * 0.75 + 0.3, 0.9 + 0.5 * math.sin(2 * math.pi * t), 0.4 * t)
    matcap = _demo_matcap()
    cx, cy, size = demo.W / 2, demo.H / 2 - 12, 440
    ctx = cv.ctx
    ctx.save()                                   # a soft contact shadow on the ground
    ctx.translate(cx, cy + size * 0.47)
    ctx.scale(1, 0.09)
    ctx.arc(0, 0, size * 0.3, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    draw_matcap_knot(cv, cx, cy, size, rot, matcap)
    _ball(cv, matcap, 96, 96, 46)


CAPABILITY = Capability(
    id='matcap-shading',
    name='Matcap shading',
    family='camera',
    group='Shader looks',
    aliases=('MatCap', 'material capture', 'lit sphere shading', 'sphere-map shading'),
    definition='A 3D form takes all its colour and shine from one painted image of a lit ball, '
               'picked by which way each bit of surface faces, so the highlights stay fixed to the '
               'camera as the form turns.',
    phrasings=('shade the 3D model with a matcap so it looks glossy without setting up lights',
               'make the object look like clay or shiny plastic using a single sphere image',
               'spin the shape while the shine and reflections stay facing the camera'),
    related=('shine-glint-sweep', 'unsharp-mask', 'low-poly-faceting', 'luma-wipe', 'heat-haze',
             'cel-shading-look'),
    api=('videobuilder.capabilities.camera.matcap_shading.matcap_render',
         'videobuilder.capabilities.camera.matcap_shading.make_matcap',
         'videobuilder.capabilities.camera.matcap_shading.matcap_lookup',
         'videobuilder.capabilities.camera.matcap_shading.draw_matcap_knot',
         'videobuilder.capabilities.camera.matcap_shading.torus_knot',
         'videobuilder.capabilities.camera.matcap_shading.rotation'),
    demo=lambda: demo.film(draw),
)
