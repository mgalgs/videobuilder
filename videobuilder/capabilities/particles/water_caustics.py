"""Water caustics: the same wavering net of light lines on a pool floor as
Caustics (`../camera/caustics.py`, which keeps the capability) -- caustics
traces rays through a wave-covered surface, this module paints the pattern
directly, a cheaper option for the same look. This module's own code stays
(a film may still import it), but it is no longer a capability of its
own."""
import math

import numpy as np
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'caustics'


def caustic_field(w, h, t, cell=320.0, speed=1.0, sharpness=8.0, octaves=5, seed=0.0):
    """A `h` x `w` float array in 0..1 of caustic light at time `t` seconds:
    thin bright ridges that meet in cells about `cell` pixels across and
    wobble as `t` moves. `sharpness` thins the ridges (higher is finer),
    `octaves` sets how many folded layers build the web, `seed` shifts to
    another stretch of water. The field is periodic in space, so it tiles."""
    tau = 2 * math.pi
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    px = (xs / cell * tau + seed * 37.0) % tau - 250.0
    py = (ys / cell * tau + seed * 53.0) % tau - 250.0
    ix, iy = px.copy(), py.copy()
    c = np.ones_like(px)
    k = 0.005
    time = t * speed * 0.5 + 23.0
    for n in range(octaves):
        tn = time * (1.0 - 3.5 / (n + 1))
        ix, iy = px + np.cos(tn - ix) + np.sin(tn + iy), py + np.sin(tn - iy) + np.cos(tn + ix)
        c += 1.0 / np.hypot(px / (np.sin(ix + tn) / k), py / (np.cos(iy + tn) / k))
    c = 1.17 - (c / octaves) ** 1.4
    return np.clip(np.abs(c), 0.0, 1.0) ** sharpness


def caustic_image(w, h, t, color='#ffffff', strength=1.0, **kw):
    """A `vb.Image` (RGBA) of `w` x `h` pixels: `color` light whose alpha is
    `caustic_field(w, h, t, **kw)` times `strength`. Lay it over a floor."""
    a = np.clip(caustic_field(w, h, t, **kw) * strength, 0.0, 1.0)
    r, g, b, _ = (round(v * 255) for v in vb.canvas.rgba(color))
    px = np.empty((h, w, 4), np.uint8)
    px[..., 0], px[..., 1], px[..., 2] = r, g, b
    px[..., 3] = (a * 255).astype(np.uint8)
    return vb.Image.from_pil(PILImage.fromarray(px, 'RGBA'))


def draw_caustics(cv, x, y, w, h, t, color='#ffffff', alpha=1.0, detail=0.4, cell=320.0, **kw):
    """Draw moving caustic light over the box (x, y, w, h) at time `t`
    seconds. The field is computed at `detail` of the box's size and scaled
    up, which keeps it soft and quick; `cell` is in the box's own pixels.
    `kw` goes to `caustic_field` (`speed`, `sharpness`, `octaves`, `seed`)."""
    s = max(detail * cv.scale_factor(), 0.02)
    gw, gh = max(2, round(w * s)), max(2, round(h * s))
    img = caustic_image(gw, gh, t, color=color, cell=cell * s, **kw)
    cv.image(img, x, y, w, h, alpha=alpha)


FLOOR, DEEP, LIGHT = '#1f7f99', '#0d3d55', '#e9fbff'


def _pool_floor(cv):
    """A tiled pool floor: a deep-to-lighter blue wash with grout lines."""
    top, bottom = vb.canvas.rgba(DEEP), vb.canvas.rgba(FLOOR)
    bands = 24
    for i in range(bands):
        u = 0.35 + 0.65 * i / (bands - 1)
        c = tuple(round(255 * (a + (b - a) * u)) for a, b in zip(top[:3], bottom[:3]))
        cv.rect(0, demo.H * i / bands, demo.W, demo.H / bands + 1, c)
    step = 120
    for gx in range(0, demo.W + 1, step):
        cv.line(gx, 0, gx, demo.H, DEEP, width=3, alpha=0.5)
    for gy in range(0, demo.H + 1, step):
        cv.line(0, gy, demo.W, gy, DEEP, width=3, alpha=0.5)


def draw(n, cv):
    cv.fill(DEEP)
    _pool_floor(cv)
    t = n / demo.FPS
    draw_caustics(cv, 0, 0, demo.W, demo.H, t, color=LIGHT, alpha=0.9, cell=420.0, speed=1.6, seed=3.0)
    cv.mark('caustics', 0, 0, demo.W, demo.H)
