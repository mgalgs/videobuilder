"""Caustics: light passing through a rippling surface is bent unevenly, so it
bunches into a net of bright, wavering lines on whatever lies beneath -- the
shimmer on the floor of a swimming pool.

The light here is traced, not painted: a grid of rays falls through a water
surface made of a few travelling waves, each ray is tipped by the slope where
it crosses, and where the rays land is counted. Where the surface focuses them
the count spikes, and those spikes are the caustic lines. The waves tile the
patch, so the pattern wraps at its edges without dark seams.

The tracing itself runs on numpy (imported when a frame is drawn, so the
registry loads without it): every ray is stepped together instead of one at
a time."""
import math
from functools import lru_cache

from PIL import Image as PILImage, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# The water surface: (waves across, waves down, height, angular speed, phase).
# Whole numbers of waves across the patch keep it tileable.
WAVES = ((4, 1, 0.8, 1.6, 0.0), (-2, 3, 0.75, -1.3, 1.3), (3, -3, 0.65, 2.0, 2.1),
         (1, 4, 0.6, -1.8, 4.0), (-5, -1, 0.5, 2.4, 5.2), (5, 3, 0.4, -2.2, 0.7),
         (-3, -4, 0.35, 1.9, 3.3))


def _np():
    import numpy
    return numpy


def caustic_light(t, gw, gh, strength=1.0, waves=WAVES, rays=2):
    """The caustic light on a `gw` x `gh` patch at time `t` seconds, as a flat
    row-major list of brightness (1 is the light's even level; the lines peak
    well above it). `strength` is how hard the surface bends the light: around
    1 gives a crisp net, lower a soft dapple, 0 an even glow. `rays` x `rays`
    rays are traced per cell; more is smoother and slower."""
    np = _np()
    tau = 2 * math.pi
    nx, ny = gw * rays, gh * rays
    x, y = np.meshgrid(np.arange(nx, dtype=np.float64), np.arange(ny, dtype=np.float64))
    dx = np.zeros((ny, nx))
    dy = np.zeros((ny, nx))
    for m, n, a, w, ph in waves:
        kx, ky = tau * m / nx, tau * n / ny  # radians per ray
        k = math.hypot(kx, ky)
        reach = 0.8 * strength * a / (k * k * rays)  # landing offset in cells per unit slope: folds at a ~ 0.7
        c = np.cos(kx * x + ky * y - w * t + ph)      # cos of the wave's phase here: its slope
        dx += reach * kx * c
        dy += reach * ky * c
    px, py = (x + 0.5) / rays - 0.5 + dx, (y + 0.5) / rays - 0.5 + dy
    ix, iy = np.floor(px), np.floor(py)
    fx, fy = px - ix, py - iy
    x0 = ix.astype(np.int64) % gw
    x1 = (x0 + 1) % gw
    y0 = iy.astype(np.int64) % gh
    y1 = (y0 + 1) % gh
    share = 1 / (rays * rays)
    bins = gw * gh
    acc = (np.bincount((y0 * gw + x0).ravel(), ((1 - fx) * (1 - fy) * share).ravel(), bins) +
           np.bincount((y0 * gw + x1).ravel(), (fx * (1 - fy) * share).ravel(), bins) +
           np.bincount((y1 * gw + x0).ravel(), ((1 - fx) * fy * share).ravel(), bins) +
           np.bincount((y1 * gw + x1).ravel(), (fx * fy * share).ravel(), bins))
    return acc.tolist()


def caustic_image(t, gw=240, gh=135, strength=1.0, color=(220, 236, 255), floor=1.0, gain=0.4,
                  waves=WAVES):
    """The caustic light at time `t` as a `vb.Image`: `color` with an alpha
    that is the light's brightness, so it lays over any surface. Light below
    `floor` (the dim cells between lines) is dropped; `gain` sets how fast the
    lines reach full strength. Draw it stretched over the lit area."""
    light = caustic_light(t, gw, gh, strength, waves)
    alpha = bytes(min(255, max(0, round(255 * (v - floor) * gain))) for v in light)
    a = PILImage.frombytes('L', (gw, gh), alpha).filter(ImageFilter.GaussianBlur(0.6))
    r, g, b = (PILImage.new('L', (gw, gh), c) for c in color)
    return vb.Image.from_pil(PILImage.merge('RGBA', (r, g, b, a)))


@lru_cache(maxsize=8)
def _cached(t, gw, gh, strength, color, floor, gain):
    return caustic_image(t, gw, gh, strength, color, floor, gain)


def caustics(cv, x, y, w, h, t, strength=1.0, color=(220, 236, 255), alpha=1.0, detail=3.0, floor=1.0,
             gain=0.4):
    """Lay moving caustic light over the box (x, y, w, h) at time `t`
    seconds: draw the lit surface first (a pool floor, a sunken card), then
    this. The light is traced on a grid of one cell per `detail` output
    pixels (lower is sharper and slower) and stretched over the box; the
    pattern's scale follows the box, so a bigger box has bigger cells.
    `strength`, `color`, `floor`, `gain` are `caustic_image`'s."""
    s = cv.scale_factor()
    gw = max(16, round(w * s / detail))
    gh = max(9, round(h * s / detail))
    img = _cached(round(t, 4), gw, gh, strength, tuple(color), floor, gain)
    cv.image(img, x, y, w, h, alpha=alpha)


def _floor(cv, x, y, w, h, tile):
    """A pool floor: deep blue with darker tile joints."""
    cv.rect(x, y, w, h, '#1d2a4a')
    for i in range(1, round(w / tile)):
        cv.rect(x + i * tile - 1, y, 2, h, '#141e38')
    for j in range(1, round(h / tile)):
        cv.rect(x, y + j * tile - 1, w, 2, '#141e38')


def draw(n, cv):
    t = n / demo.FPS
    w, h = 800, 440
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    _floor(cv, x, y, w, h, 50)
    caustics(cv, x, y, w, h, 1.5 + t)
    cv.mark('pool', x, y, w, h)


CAPABILITY = Capability(
    id='caustics',
    name='Caustics',
    family='camera',
    group='Lighting & surface',
    aliases=('light caustics', 'refracted light patterns', 'pool light'),
    definition='Light bent by a moving, uneven surface such as water gathers into a net of bright, '
               'wavering lines that crawl across whatever lies underneath.',
    phrasings=('make it look like sunlight dancing on the bottom of a pool',
               'add that rippling underwater light pattern over the floor',
               'shimmering water reflections moving across the surface'),
    related=('water-caustics', 'refraction-ripple', 'gooch-shading', 'cymatics', 'ripple', 'ripple-rings'),
    api=('videobuilder.capabilities.camera.caustics.caustics',
         'videobuilder.capabilities.camera.caustics.caustic_image',
         'videobuilder.capabilities.camera.caustics.caustic_light'),
    demo=lambda: demo.film(draw),
)
