"""Burning Ship fractal: the Mandelbrot iteration with both parts of z folded
to their absolute values before squaring, which grows a jagged, flame-lit
"ship" with masts and rigging; usually shown as a slow zoom into its detail."""
import math
from functools import lru_cache

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# The whole set, ship upright (imaginary axis pointing down the frame).
HOME = (-0.4, -0.55)
HOME_SPAN = 4.2
# The small ship riding on the big one's left antenna: the classic zoom target.
LITTLE_SHIP = (-1.7615, -0.0285)

FIRE = ((0, 0, 0), (60, 6, 4), (170, 36, 12), (239, 91, 76), (255, 170, 60), (255, 236, 170), (255, 255, 255))


def burning_ship(cx, cy, max_iter=100):
    """The smooth escape count of point c = cx + i*cy under the Burning Ship
    map z -> (|Re z| + i|Im z|)^2 + c, from z = 0: a float in [0, max_iter)
    for points that escape, None for points that never do (the set)."""
    x = y = 0.0
    for i in range(max_iter):
        xx, yy = x * x, y * y
        if xx + yy > 256.0:
            return i + 1 - math.log2(math.log2(xx + yy) / 2)  # smooth: no banding between counts
        y = 2 * abs(x * y) + cy
        x = xx - yy + cx
    return None


def fire_palette(t, stops=FIRE):
    """`t` in [0, 1] -> an RGB tuple along `stops` (default black through red
    and orange to white, the usual "burning" colouring)."""
    t = vb.clamp01(t) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


@lru_cache(maxsize=8)
def burning_ship_image(width, height, center=HOME, span=HOME_SPAN, max_iter=100, inside=(0, 0, 0),
                       stops=FIRE, cycles=1.0):
    """A `width` x `height` PIL image of the Burning Ship set: `span` units of
    the complex plane across, centred on `center` (re, im), imaginary axis
    pointing down so the ship stands upright. Escaping points are coloured by
    `fire_palette(stops)` of their smooth count (wrapped `cycles` times),
    points in the set get `inside`. Cached, so redrawing a frame is free."""
    px = span / width
    x0, y0 = center[0] - span / 2, center[1] - px * height / 2
    lut = [fire_palette(k / 255, stops) for k in range(256)]
    data = bytearray()
    for j in range(height):
        cy = y0 + (j + 0.5) * px
        for i in range(width):
            v = burning_ship(x0 + (i + 0.5) * px, cy, max_iter)
            if v is None:
                data.extend(inside)
            else:
                # a gentle power lifts the edges into flame and keeps empty space dark
                t = (max(v, 0) / max_iter) ** 0.65 * cycles % 1.0
                data.extend(lut[min(255, int(t * 255))])
    return PILImage.frombytes('RGB', (width, height), bytes(data))


def draw_burning_ship(cv, x, y, w, h, center=HOME, span=HOME_SPAN, max_iter=None, detail=480, **kw):
    """Draw the Burning Ship set into the box (x, y, w, h), `span` units of
    the plane across, centred on `center`. Computed in pure Python at up to
    `detail` samples across (fewer for small previews) and smoothed up to
    the box. `max_iter` defaults to rising with zoom so deep views keep
    their edges. `kw` goes to `burning_ship_image` (`inside`, `stops`,
    `cycles`). For a zoom, shrink `span` exponentially over time."""
    gw = max(8, min(detail, round(w * cv.scale_factor())))
    gh = max(8, round(gw * h / w))
    if max_iter is None:
        max_iter = int(60 + 30 * max(0.0, math.log2(HOME_SPAN / span)))
    # quantise so near-identical frames share the cache
    img = burning_ship_image(gw, gh, (round(center[0], 12), round(center[1], 12)), float(f'{span:.6g}'),
                             max_iter, **kw)
    cv.image(vb.Image.from_pil(img), x, y, w, h)


def zoom_span(p, start=HOME_SPAN, depth=60.0):
    """The span at progress `p` of a smooth zoom that ends `depth` times
    closer: exponential in scale, so the dive feels like constant speed."""
    return start / depth ** vb.clamp01(p)


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.9)
    p = p * p * (3 - 2 * p)  # ease in and out of the dive
    span = zoom_span(p, depth=50.0)
    # zoom about the little ship, letting it drift to the middle of the frame as we close in
    k = span / HOME_SPAN * (1 - p)
    c = (LITTLE_SHIP[0] + (HOME[0] - LITTLE_SHIP[0]) * k, LITTLE_SHIP[1] + (HOME[1] - LITTLE_SHIP[1]) * k)
    draw_burning_ship(cv, 0, 0, demo.W, demo.H, center=c, span=span,
                      inside=(20, 21, 26), detail=400)
    cv.mark('fractal', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='burning-ship-fractal',
    name='Burning Ship fractal',
    family='particles',
    group='Fractals',
    aliases=('Burning Ship', 'burning ship set', 'abs Mandelbrot'),
    definition='A Mandelbrot-style escape-time picture whose folded formula grows a jagged, flame-coloured '
               'ship shape, usually shown diving into ever smaller copies of itself.',
    phrasings=('zoom into a fiery fractal that looks like a burning ship',
               'the burning ship set, coloured like flames',
               'a dark fractal with glowing orange edges that we fly into'),
    related=('fractal-brownian-motion', 'doom-style-fire', 'confetti', 'displacement-map', 'recursive-tree',
             'circle-packing'),
    api=('videobuilder.capabilities.particles.burning_ship_fractal.draw_burning_ship',
         'videobuilder.capabilities.particles.burning_ship_fractal.burning_ship_image',
         'videobuilder.capabilities.particles.burning_ship_fractal.burning_ship',
         'videobuilder.capabilities.particles.burning_ship_fractal.zoom_span'),
    demo=lambda: demo.film(draw),
)
