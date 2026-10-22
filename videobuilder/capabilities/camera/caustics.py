"""Caustics: light passing through a rippling surface is bent unevenly, so it
bunches into a net of bright, wavering lines on whatever lies beneath -- the
shimmer on the floor of a swimming pool.

The light here is traced, not painted: a grid of rays falls through a water
surface made of a few travelling waves, each ray is tipped by the slope where
it crosses, and where the rays land is counted. Where the surface focuses them
the count spikes, and those spikes are the caustic lines. The waves tile the
patch, so the pattern wraps at its edges without dark seams."""
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


def caustic_light(t, gw, gh, strength=1.0, waves=WAVES, rays=2):
    """The caustic light on a `gw` x `gh` patch at time `t` seconds, as a flat
    row-major list of brightness (1 is the light's even level; the lines peak
    well above it). `strength` is how hard the surface bends the light: around
    1 gives a crisp net, lower a soft dapple, 0 an even glow. `rays` x `rays`
    rays are traced per cell; more is smoother and slower."""
    tau = 2 * math.pi
    nx, ny = gw * rays, gh * rays
    terms = []
    for m, n, a, w, ph in waves:
        kx, ky = tau * m / nx, tau * n / ny  # radians per ray
        k = math.hypot(kx, ky)
        reach = 0.8 * strength * a / (k * k * rays)  # landing offset in cells per unit slope: folds at a ~ 0.7
        cols = [kx * x for x in range(nx)]
        rows = [ky * y - w * t + ph for y in range(ny)]
        terms.append(([math.cos(c) for c in cols], [math.sin(c) for c in cols],
                      [math.cos(r) for r in rows], [math.sin(r) for r in rows], reach * kx, reach * ky))
    acc = [0.0] * (gw * gh)
    share = 1 / (rays * rays)
    for y in range(ny):
        row_terms = [(cc, sc, cr[y], sr[y], ax, ay) for cc, sc, cr, sr, ax, ay in terms]
        for x in range(nx):
            dx = dy = 0.0
            for cc, sc, cy, sy, ax, ay in row_terms:
                c = cc[x] * cy - sc[x] * sy  # cos of the wave's phase here: its slope
                dx += ax * c
                dy += ay * c
            px, py = (x + 0.5) / rays - 0.5 + dx, (y + 0.5) / rays - 0.5 + dy
            ix, iy = math.floor(px), math.floor(py)
            fx, fy = px - ix, py - iy
            x0, x1 = ix % gw, (ix + 1) % gw
            r0, r1 = (iy % gh) * gw, ((iy + 1) % gh) * gw
            acc[r0 + x0] += (1 - fx) * (1 - fy) * share
            acc[r0 + x1] += fx * (1 - fy) * share
            acc[r1 + x0] += (1 - fx) * fy * share
            acc[r1 + x1] += fx * fy * share
    return acc


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
